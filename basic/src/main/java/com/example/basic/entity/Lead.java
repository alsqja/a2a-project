package com.example.basic.entity;

import com.example.basic.global.common.BaseEntity;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
@Entity
@Table(name = "`lead`")
public class Lead extends BaseEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "lead_score")
    private Double leadScore;

    @ManyToOne
    @JoinColumn(name = "source_company_id", nullable = false)
    private Company sourceCompany;

    @ManyToOne
    @JoinColumn(name = "lead_company_id", nullable = false)
    private Company leadCompany;
}
