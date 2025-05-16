package com.example.basic.dto;

import com.example.basic.entity.Lead;
import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public class LeadResDto {

    private final Long id;
    private final String leadCompanyName;
    private final Double leadScore;
    private final String status; // status 필드 추가

    public LeadResDto(Lead lead) {
        this.id = lead.getId();
        this.leadCompanyName = lead.getLeadCompany().getCompanyName();
        this.leadScore = lead.getLeadScore();
        this.status = "RECOMMENDED";
    }

    // JSON 파일 데이터용 생성자 추가
    public LeadResDto(Long id, String leadCompanyName, Double leadScore) {
        this.id = id;
        this.leadCompanyName = leadCompanyName;
        this.leadScore = leadScore;
        this.status = "RECOMMENDED";
    }
}