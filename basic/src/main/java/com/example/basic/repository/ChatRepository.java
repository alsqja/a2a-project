package com.example.basic.repository;

import com.example.basic.entity.Chat;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ChatRepository extends JpaRepository<Chat, Long> {

    List<Chat> findAllByChatRoomId(Long chatRoomId);
}
