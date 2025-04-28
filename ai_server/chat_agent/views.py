import asyncio
import json
import queue
import threading

from django.db import close_old_connections
from django.http import HttpResponse, StreamingHttpResponse
from django.template.loader import render_to_string
from django.views import View
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from chat_agent.services.agent_chat_service import run_agent_conversation
from chat_agent.services.chat_service import ChatService
from chat_agent.services.chat_summary_service import create_chat_summary
from chat_agent.services.lead_details_service import LeadDetailsService
from chat_agent.services.pdf_service import PDFAnalysisService
from asgiref.sync import async_to_sync

class ChatSummaryView(APIView):
    def post(self, request, room_id):

        try:
            lead_id = request.data.get('leadId')

            response = async_to_sync(create_chat_summary)(room_id, lead_id)
        except Exception as e:
            print(e)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "message": "대화 요약 출력 완료",
            "data": response,
        }, status=status.HTTP_200_OK)


class A2aChatView(View):
    def get(self, request, lead_id):
        def event_stream():
            # 스레드 간 통신을 위한 큐
            q = queue.Queue()

            # 비동기 작업을 실행할 스레드
            def worker():
                close_old_connections()

                async def process():
                    async for chat in run_agent_conversation(lead_id):
                        formatted_data = f"data: {json.dumps(chat)}\n\n"
                        q.put(formatted_data)
                    # 작업 완료 표시
                    q.put(None)

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(process())
                finally:
                    loop.close()

            # 백그라운드에서 비동기 작업 시작
            t = threading.Thread(target=worker)
            t.daemon = True
            t.start()

            # 큐에서 결과를 하나씩 가져와 반환
            while True:
                result = q.get()
                if result is None:  # 작업 완료 신호
                    break
                yield result

        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        return response

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

class LeadDataView(APIView):
    def post(self, request):
        """
        회사 이름을 받아 해당 회사의 상세 정보를 반환합니다.
        """
        search_company_name = request.data.get('company_name')

        if not search_company_name:
            return Response(
                {"error": "company_name is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 여기서 비즈니스 로직을 통해 회사 정보를 가져옵니다
        result = LeadDetailsService().extract_info(search_company_name)

        # HTML 템플릿 렌더링
        html_content = render_to_string('lead_data_template.html', result)

        # HTML 콘텐츠 직접 반환
        return HttpResponse(html_content, content_type='text/html')
