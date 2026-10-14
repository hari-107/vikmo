import re
import difflib
from decimal import Decimal
from django.db.models import Q
from core.models import Product, Dealer
from core.services import create_draft_order as service_create_draft_order

# Automotive domain keywords and categories for typo correction
COMMON_AUTO_VOCABULARY = [
    "silencer", "exhaust", "muffler", "pipe",
    "brake", "pad", "pads", "disc", "shoe", "lever", "caliper",
    "oil", "filter", "filters", "coolant", "lubricant", "grease",
    "chain", "sprocket", "drive", "belt", "pulley",
    "spark", "plug", "ignition", "coil", "cable",
    "clutch", "throttle", "accelerator",
    "tyre", "tire", "tube", "rim", "wheel",
    "mirror", "battery", "horn", "light", "bulb", "headlight", "taillight", "indicator",
    "relay", "fuse", "switch", "handlebar", "grip",
    "suspension", "fork", "shock", "absorber",
    "gasket", "bearing", "piston", "ring", "carburetor", "radiator",
    "guard", "crash", "tank", "cover"
]

STOP_WORDS = {
    "did", "you", "have", "do", "u", "can", "i", "get", "show", "me",
    "what", "is", "are", "the", "for", "a", "an", "of", "in", "any",
    "please", "check", "find", "looking", "want", "need", "we", "has",
    "there", "some", "units", "pieces", "stock", "price", "cost"
}


def normalize_and_correct_query(query: str) -> tuple[str, dict]:
    """
    Cleans raw query text and applies typo-tolerant corrections
    using difflib against automotive domain vocabulary.
    Returns (cleaned_query, corrections_dict).
    """
    if not query:
        return "", {}

    # Check if query is already an exact SKU pattern
    sku_match = re.search(r"\b[A-Z]{3}-\d{4}\b", query.upper())
    if sku_match:
        return sku_match.group(0), {}

    # Tokenize and strip punctuation
    clean_text = re.sub(r"[^a-zA-Z0-9\s-]", " ", query.lower())
    tokens = [t.strip() for t in clean_text.split() if t.strip()]

    # Filter out common conversational stop words
    filtered_tokens = [t for t in tokens if t not in STOP_WORDS]
    if not filtered_tokens:
        filtered_tokens = tokens  # fallback if all words were filtered

    corrections = {}
    normalized_tokens = []

    for token in filtered_tokens:
        # If token is very short, keep as is
        if len(token) <= 2:
            normalized_tokens.append(token)
            continue

        # Check exact or close match in vocabulary
        if token in COMMON_AUTO_VOCABULARY:
            normalized_tokens.append(token)
        else:
            matches = difflib.get_close_matches(token, COMMON_AUTO_VOCABULARY, n=1, cutoff=0.6)
            if matches:
                corrections[token] = matches[0]
                normalized_tokens.append(matches[0])
            else:
                normalized_tokens.append(token)

    return " ".join(normalized_tokens), corrections


class AssistantToolRegistry:
    def __init__(self, dealer_id: int):
        self.dealer_id = dealer_id
        self.recorded_tool_calls = []
        self.recorded_actions = []
        self.cited_skus = set()
        self._created_orders_cache = {}  # prevents duplicate draft orders in the same turn

    def search_parts(self, query: str = "", vehicle: str = None) -> dict:
        """Search catalogue for spare parts matching query and optional vehicle fitment."""
        arg_dict = {}
        if query is not None:
            arg_dict["query"] = str(query)
        if vehicle is not None:
            arg_dict["vehicle"] = str(vehicle)

        self.recorded_tool_calls.append({
            "name": "search_parts",
            "arguments": arg_dict,
        })

        raw_query = (query or "").strip()
        vehicle_filter = (vehicle or "").strip()

        # Step 1: Check exact SKU match directly
        sku_candidate = raw_query.upper()
        if re.match(r"^[A-Z]{3}-\d{4}$", sku_candidate):
            exact_p = Product.objects.filter(sku__iexact=sku_candidate).first()
            if exact_p:
                self.cited_skus.add(exact_p.sku)
                return {
                    "count": 1,
                    "products": [{
                        "sku": exact_p.sku,
                        "name": exact_p.name,
                        "category": exact_p.category,
                        "brand": exact_p.brand,
                        "vehicle_fitment": exact_p.vehicle_fitment,
                        "price": f"{exact_p.price:.2f}",
                        "stock": exact_p.stock,
                    }],
                }

        # Step 2: Normalize and correct typos in query
        normalized_query, corrections = normalize_and_correct_query(raw_query)

        qs = Product.objects.all()
        if vehicle_filter:
            qs = qs.filter(vehicle_fitment__icontains=vehicle_filter)

        search_terms = normalized_query.split() if normalized_query else []
        if not search_terms and raw_query:
            search_terms = raw_query.split()

        if search_terms:
            q_filter = Q()
            for term in search_terms:
                q_filter |= (
                    Q(sku__icontains=term)
                    | Q(name__icontains=term)
                    | Q(category__icontains=term)
                    | Q(brand__icontains=term)
                    | Q(vehicle_fitment__icontains=term)
                )
            qs = qs.filter(q_filter)

        # Rank results by relevance match score: name > fitment > category > brand
        scored = []
        for p in qs:
            score = 0
            sku_l = p.sku.lower()
            name_l = p.name.lower()
            fit_l = p.vehicle_fitment.lower()
            cat_l = p.category.lower()
            brand_l = p.brand.lower()

            for term in search_terms:
                t_l = term.lower()
                t_stem = t_l[:-1] if t_l.endswith('s') and len(t_l) > 3 else t_l
                if t_l == sku_l:
                    score += 50
                if t_l in sku_l:
                    score += 15
                if t_l in name_l or t_stem in name_l:
                    score += 15
                if t_l in fit_l or t_stem in fit_l:
                    score += 10
                if t_l in cat_l or t_stem in cat_l:
                    score += 6
                if t_l in brand_l or t_stem in brand_l:
                    score += 4
            scored.append((score, p))

        scored.sort(key=lambda x: (-x[0], x[1].sku))
        products = [p for _, p in scored[:15]]

        results = []
        for p in products:
            self.cited_skus.add(p.sku)
            results.append({
                "sku": p.sku,
                "name": p.name,
                "category": p.category,
                "brand": p.brand,
                "vehicle_fitment": p.vehicle_fitment,
                "price": f"{p.price:.2f}",
                "stock": p.stock,
            })

        out = {"count": len(results), "products": results[:10]}
        if corrections:
            out["interpreted_corrections"] = corrections
        return out

    def check_stock(self, sku: str = "") -> dict:
        """Check current available stock for a specific product SKU."""
        clean_sku = str(sku).strip().upper() if sku else ""
        self.recorded_tool_calls.append({
            "name": "check_stock",
            "arguments": {"sku": sku},
        })

        if not clean_sku:
            return {"error": "SKU parameter is required", "available": False}

        product = Product.objects.filter(sku__iexact=clean_sku).first()
        if not product:
            return {
                "error": f"Product with SKU '{sku}' not found",
                "sku": sku,
                "available": False,
                "stock": 0,
            }

        self.cited_skus.add(product.sku)
        return {
            "sku": product.sku,
            "name": product.name,
            "stock": product.stock,
            "price": f"{product.price:.2f}",
            "available": product.stock > 0,
        }

    def create_draft_order(self, items: list = None) -> dict:
        """
        Create a draft order for specified items. Dealer ID is server-controlled.
        Includes duplicate-creation protection across retries and failovers.
        """
        self.recorded_tool_calls.append({
            "name": "create_draft_order",
            "arguments": {"items": items},
        })

        if not items or not isinstance(items, list):
            return {"error": "Items list cannot be empty"}

        cleaned_items = []
        for it in items:
            if not isinstance(it, dict):
                return {"error": "Invalid item structure: each item must be a dictionary"}
            sku = str(it.get("sku", "")).strip().upper()
            try:
                qty = int(it.get("quantity", 0))
            except (ValueError, TypeError):
                return {"error": f"Invalid quantity for SKU {sku}"}

            if qty < 1:
                return {"error": f"Quantity for SKU {sku} must be >= 1"}
            cleaned_items.append({"sku": sku, "quantity": qty})

        # Cache key to prevent duplicate draft order creation on provider failovers
        cache_key = tuple(sorted((it["sku"], it["quantity"]) for it in cleaned_items))
        if cache_key in self._created_orders_cache:
            return self._created_orders_cache[cache_key]

        try:
            order_data, _, _ = service_create_draft_order(
                dealer_id=self.dealer_id,
                items_data=cleaned_items,
            )
            order_number = order_data["order_number"]
            self.recorded_actions.append({
                "type": "draft_order_created",
                "order_number": order_number,
            })
            for it in cleaned_items:
                self.cited_skus.add(it["sku"])

            res = {
                "success": True,
                "order_number": order_number,
                "status": "DRAFT",
                "subtotal": order_data["subtotal"],
                "tax_total": order_data["tax_total"],
                "grand_total": order_data["grand_total"],
            }
            self._created_orders_cache[cache_key] = res
            return res
        except Exception as e:
            return {"error": str(e)}
