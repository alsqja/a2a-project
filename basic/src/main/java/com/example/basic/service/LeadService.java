package com.example.basic.service;

import com.example.basic.dto.LeadResDto;
import com.example.basic.repository.LeadRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class LeadService {

    private final LeadRepository leadRepository;

    public List<LeadResDto> findAllLeadsByCompanyId(Long companyId) {

        return leadRepository.findBySourceCompanyId(companyId).stream().map(LeadResDto::new).toList();
    }
}
