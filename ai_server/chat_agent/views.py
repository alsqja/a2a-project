import asyncio

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from chat_agent.services.agent_chat_service import run_agent_conversation
from chat_agent.services.chat_service import ChatService
from chat_agent.services.pdf_service import PDFAnalysisService
from asgiref.sync import async_to_sync

class A2aChatView(APIView):
    def post(self, request):
        lead_id = request.data.get('lead_id')

        try:
            async_to_sync(run_agent_conversation)(lead_id=lead_id)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({'message': "협상 완료"}, status=status.HTTP_200_OK)

class ChatAgentView(APIView):
    def post(self, request):
        company_id = request.data.get('companyId')
        contents = request.data.get('contents')
        room_id = request.data.get('roomId')

        chat_service = ChatService()
        result = chat_service.send_message(company_id, contents, room_id)

        return Response({
            "message": "메세지 응답 성공",
            "data": result
        })

class PDFAnalysisView(APIView):
    def post(self, request, file_id=None):
        """
        PDF 파일을 분석하고 DB에 저장하는 API 엔드포인트
        """
        try:
            # profile_id가 URL에서 오지 않았다면 body에서 확인
            if file_id is None:
                file_id = request.data.get('file_id')
                if not file_id:
                    return Response(
                        {"error": "file_id is required"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            pdf_service = PDFAnalysisService()
            analysis = pdf_service.analyze_company_pdf(file_id)

            if not analysis:
                return Response(
                    {"error": "Failed to analyze PDF"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            return Response({
                "message": "PDF analysis completed successfully",
                "data": analysis
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )