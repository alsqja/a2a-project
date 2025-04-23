package com.example.basic.controller;

import com.example.basic.dto.CompanyResDto;
import com.example.basic.global.common.CommonResDto;
import com.example.basic.service.CompanyService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/companies")
public class CompanyController {

    private final CompanyService companyService;

    @GetMapping("/{id}")
    public ResponseEntity<CommonResDto<CompanyResDto>> findById(@PathVariable("id") Long id) {

        return new ResponseEntity<>(new CommonResDto<>("회사 정보 조회 성공", companyService.findById(id)), HttpStatus.OK);
    }
}
