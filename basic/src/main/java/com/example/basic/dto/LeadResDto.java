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

    public LeadResDto(Lead lead) {
        this.id = lead.getId();
        this.leadCompanyName = lead.getLeadCompany().getCompanyName();
        this.leadScore = lead.getLeadScore();
    }
}
