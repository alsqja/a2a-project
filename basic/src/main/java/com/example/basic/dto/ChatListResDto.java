package com.example.basic.dto;

import lombok.AllArgsConstructor;
import lombok.Getter;

import java.util.List;

@Getter
@AllArgsConstructor
public class ChatListResDto {

    private final Long roomId;
    private final List<ChatResDto> chats;
}
