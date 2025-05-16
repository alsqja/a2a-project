package com.example.basic.service;

import com.example.basic.dto.LeadResDto;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class LeadService {

    //    private final LeadRepository leadRepository;
//
//    public List<LeadResDto> findAllLeadsByCompanyId(Long companyId) {
//
//        return leadRepository.findBySourceCompanyId(companyId).stream().map(LeadResDto::new).toList();
//    }
    private final ObjectMapper objectMapper = new ObjectMapper();

    public List<LeadResDto> findAllLeadsByCompanyId(Long companyId) {
        try {
            // JSON 파일 읽기 (resources 폴더)
            ClassPathResource resource = new ClassPathResource("data/extracted_companies.json");

            // JSON 데이터를 List<Map>으로 파싱
            List<Map<String, Object>> companies = objectMapper.readValue(
                    resource.getInputStream(),
                    new TypeReference<List<Map<String, Object>>>() {
                    }
            );

            // 데이터를 LeadResDto 리스트로 변환
            List<LeadResDto> allLeads = companies.stream()
                    .map(company -> new LeadResDto(
                            ((Number) company.get("lead_company_id")).longValue(),
                            (String) company.get("lead_company_name"),
                            ((Number) company.get("lead_score")).doubleValue()
                    ))
                    .collect(Collectors.toList());

            // 리스트를 섞고 최대 30개 반환
            Collections.shuffle(allLeads);
            return allLeads.stream().limit(30).collect(Collectors.toList());

        } catch (IOException e) {
            e.printStackTrace();
            // 에러 발생 시 빈 리스트 반환
            return new ArrayList<>();
        }
    }
}
