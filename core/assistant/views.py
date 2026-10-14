from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.models import Dealer
from core.exceptions import ApiValidationError
from .agent import AssistantEngine


class AssistantChatView(APIView):
    def post(self, request):
        data = request.data
        if not isinstance(data, dict):
            raise ApiValidationError("Invalid request body. Expected JSON object.")

        session_id = data.get("session_id")
        dealer_id = data.get("dealer_id")
        message = data.get("message")

        if not session_id or not str(session_id).strip():
            raise ApiValidationError(
                "session_id is required",
                details=[{"field": "session_id", "error": "Required"}],
            )

        if dealer_id is None:
            raise ApiValidationError(
                "dealer_id is required",
                details=[{"field": "dealer_id", "error": "Required"}],
            )

        try:
            dealer_id = int(dealer_id)
        except (ValueError, TypeError):
            raise ApiValidationError(
                "dealer_id must be an integer",
                details=[{"field": "dealer_id", "error": "Must be integer"}],
            )

        if not Dealer.objects.filter(id=dealer_id).exists():
            raise ApiValidationError(
                f"Dealer with id {dealer_id} does not exist",
                details=[{"field": "dealer_id", "error": "Not found"}],
            )

        if message is None or not str(message).strip():
            raise ApiValidationError(
                "message is required",
                details=[{"field": "message", "error": "Required"}],
            )

        engine = AssistantEngine(session_id=str(session_id).strip(), dealer_id=dealer_id)
        result = engine.run(message=str(message).strip())

        return Response(result, status=status.HTTP_200_OK)
