package com.example.basic.service;

import com.example.basic.dto.CompanyResDto;
import com.example.basic.entity.Company;
import com.example.basic.repository.CompanyRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
@RequiredArgsConstructor
public class CompanyService {

    private final CompanyRepository companyRepository;

    public CompanyResDto findById(Long id) {

        Company company = companyRepository.findById(id).orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "company not found"));

        return new CompanyResDto(company);
    }
}
