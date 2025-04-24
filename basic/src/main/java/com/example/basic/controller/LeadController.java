package com.example.basic.controller;

import com.example.basic.dto.ChatListResDto;
import com.example.basic.global.common.CommonResDto;
import com.example.basic.service.ChatService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/leads")
public class LeadController {

    private final ChatService chatService;

    @GetMapping("/{leadId}/chats")
    public ResponseEntity<CommonResDto<ChatListResDto>> getLeadChats(@PathVariable Long leadId) {

        return new ResponseEntity<>(new CommonResDto<>("채팅 내역 조회 성공", chatService.findChatsByLeadId(leadId)), HttpStatus.OK);
    }
}
