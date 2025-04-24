package com.example.basic.service;

import com.example.basic.dto.ChatListResDto;
import com.example.basic.dto.ChatResDto;
import com.example.basic.entity.ChatRoom;
import com.example.basic.repository.ChatRepository;
import com.example.basic.repository.ChatRoomRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@Service
@RequiredArgsConstructor
public class ChatService {

    private final ChatRepository chatRepository;
    private final ChatRoomRepository chatRoomRepository;

    public ChatListResDto findChatsByLeadId(Long leadId) {

        ChatRoom chatRoom = chatRoomRepository.findByLeadId(leadId).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "lead not found"));

        List<ChatResDto> result = chatRepository.findAllByChatRoomId(chatRoom.getId()).stream().map(ChatResDto::new).toList();

        return new ChatListResDto(chatRoom.getId(), result);
    }
}
