from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler
from django.http import Http404
from django.core.exceptions import ValidationError as DjangoValidationError


class BaseApiException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "VALIDATION_ERROR"
    default_detail = "Bad request"

    def __init__(self, message=None, code=None, details=None, status_code=None):
        if status_code is not None:
            self.status_code = status_code
        self.code = code or self.default_code
        self.message = message or self.default_detail
        self.details = details if details is not None else []
        super().__init__(detail=self.message, code=self.code)


class ApiValidationError(BaseApiException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "VALIDATION_ERROR"
    default_detail = "Validation error"


class ApiNotFoundError(BaseApiException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "NOT_FOUND"
    default_detail = "Not found"


class ApiDuplicateError(BaseApiException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "DUPLICATE"
    default_detail = "Resource already exists"


class ApiInsufficientStockError(BaseApiException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "INSUFFICIENT_STOCK"
    default_detail = "Insufficient stock"


class ApiInvalidTransitionError(BaseApiException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "INVALID_TRANSITION"
    default_detail = "Invalid status transition"


class ApiOrderLockedError(BaseApiException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "ORDER_LOCKED"
    default_detail = "Order is locked and cannot be edited"


class ApiIdempotencyConflictError(BaseApiException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "IDEMPOTENCY_CONFLICT"
    default_detail = "Idempotency key reused with different request payload"


class ApiSupplierUnavailableError(BaseApiException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_code = "SUPPLIER_UNAVAILABLE"
    default_detail = "Supplier feed unavailable"


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, BaseApiException):
        from rest_framework.response import Response
        return Response(
            {
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
            status=exc.status_code,
        )

    if isinstance(exc, Http404):
        from rest_framework.response import Response
        return Response(
            {
                "error": {
                    "code": "NOT_FOUND",
                    "message": str(exc) if str(exc) else "Resource not found",
                    "details": [],
                }
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if response is not None:
        code = "VALIDATION_ERROR"
        if response.status_code == 404:
            code = "NOT_FOUND"
        elif response.status_code == 409:
            code = "CONFLICT"

        details = []
        message = "An error occurred"

        if isinstance(response.data, dict):
            if "detail" in response.data:
                message = str(response.data["detail"])
            else:
                field_errors = []
                for field, errs in response.data.items():
                    err_msg = ", ".join(str(e) for e in (errs if isinstance(errs, list) else [errs]))
                    field_errors.append(f"{field}: {err_msg}")
                    details.append({"field": field, "error": err_msg})
                if field_errors:
                    message = "; ".join(field_errors)
        elif isinstance(response.data, list):
            message = "; ".join(str(e) for e in response.data)

        response.data = {
            "error": {
                "code": code,
                "message": message,
                "details": details,
            }
        }
        return response

    return response
