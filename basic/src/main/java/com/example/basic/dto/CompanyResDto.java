package com.example.basic.dto;

import com.example.basic.entity.Company;
import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public class CompanyResDto {

    private final Long id;
    private final String companyName;
    private final String industry;
    private final Double sales;
    private final Double totalFunding;
    private final String address;
    private final String email;
    private final String phoneNumber;
    private final String homepage;
    private final String keyExecutive;

    public CompanyResDto(Company company) {
        this.id = company.getId();
        this.companyName = company.getCompanyName();
        this.industry = company.getIndustry();
        this.sales = company.getSales();
        this.totalFunding = company.getTotalFunding();
        this.address = company.getAddress();
        this.email = company.getEmail();
        this.phoneNumber = company.getPhoneNumber();
        this.homepage = company.getHomepage();
        this.keyExecutive = company.getKeyExecutive();
    }
}
