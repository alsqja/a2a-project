package com.example.basic.controller;

import com.example.basic.dto.CompanyResDto;
import com.example.basic.dto.LeadResDto;
import com.example.basic.global.common.CommonResDto;
import com.example.basic.service.CompanyService;
import com.example.basic.service.LeadService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/companies")
public class CompanyController {

    private final CompanyService companyService;
    private final LeadService leadService;

    @GetMapping("/{id}/leads")
    public ResponseEntity<CommonResDto<List<LeadResDto>>> getAllLeads(@PathVariable Long id) {

        return new ResponseEntity<>(new CommonResDto<>("리드 추천 목록 조회 성공", leadService.findAllLeadsByCompanyId(id)), HttpStatus.OK);
    }

    @GetMapping("/{id}")
    public ResponseEntity<CommonResDto<CompanyResDto>> findById(@PathVariable Long id) {

        return new ResponseEntity<>(new CommonResDto<>("회사 정보 조회 성공", companyService.findById(id)), HttpStatus.OK);
    }
}
