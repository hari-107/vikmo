from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .supplier_sync import run_supplier_sync


class SupplierSyncView(APIView):
    def post(self, request):
        result = run_supplier_sync()
        return Response(result, status=status.HTTP_200_OK)
