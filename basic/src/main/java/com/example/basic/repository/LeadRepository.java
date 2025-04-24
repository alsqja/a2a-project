package com.example.basic.repository;

import com.example.basic.entity.Lead;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface LeadRepository extends JpaRepository<Lead, Long> {

    List<Lead> findBySourceCompanyId(Long companyId);
}
