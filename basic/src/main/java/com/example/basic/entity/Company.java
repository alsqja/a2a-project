package com.example.basic.entity;

import com.example.basic.global.common.BaseEntity;
import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.ArrayList;
import java.util.List;

@Getter
@NoArgsConstructor
@Entity
@Table(name = "company")
public class Company extends BaseEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "company_name", nullable = false)
    private String companyName;

    @Column(name = "industry")
    private String industry;

    @Column(name = "sales")
    private Double sales;

    @Column(name = "total_funding")
    private Double totalFunding;

    @Column(name = "address")
    private String address;

    @Column(name = "email")
    private String email;

    @Column(name = "homepage")
    private String homepage;

    @Column(name = "key_executive")
    private String keyExecutive;

    @Column(name = "phone_number")
    private String phoneNumber;

    @OneToMany(mappedBy = "sourceCompany", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Lead> sourceCompanies = new ArrayList<>();

    @OneToMany(mappedBy = "leadCompany", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Lead> leadCompanies = new ArrayList<>();
}
