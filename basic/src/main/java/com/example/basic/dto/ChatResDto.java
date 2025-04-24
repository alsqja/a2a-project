package com.example.basic.dto;

import com.example.basic.entity.Chat;
import lombok.AllArgsConstructor;
import lombok.Getter;

import java.time.LocalDateTime;

@Getter
@AllArgsConstructor
public class ChatResDto {

    private final Long id;
    private final Long fromId;
    private final Long toId;
    private final String fromCompanyName;
    private final String toCompanyName;
    private final String contents;
    private final LocalDateTime createdAt;
    private final LocalDateTime updatedAt;

    public ChatResDto(Chat chat) {
        this.id = chat.getId();
        this.fromId = chat.getFromCompany().getId();
        this.toId = chat.getToCompany().getId();
        this.fromCompanyName = chat.getFromCompany().getCompanyName();
        this.toCompanyName = chat.getToCompany().getCompanyName();
        this.contents = chat.getContents();
        this.createdAt = chat.getCreatedAt();
        this.updatedAt = chat.getUpdatedAt();
    }
}
