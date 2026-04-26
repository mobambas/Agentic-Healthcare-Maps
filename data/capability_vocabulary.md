# Capability Vocabulary

Canonical `Capability.name` values used by `data/gold_labels.jsonl`. Evidence remains verbatim in `evidence_quote`.

## Controlled Vocabulary

- `ambulance_service`
- `anaesthesiology`
- `ayurveda`
- `ayushman_card_accepted`
- `blood_bank`
- `blood_storage_unit`
- `dental_services`
- `dialysis`
- `emergency_care_24x7`
- `homeopathy`
- `icu_services`
- `inpatient_services`
- `laboratory_services`
- `obstetric_surgery_caesarean`
- `oncology_services`
- `operation_theatre`
- `outpatient_services`
- `pharmacy_onsite`
- `physiotherapy`
- `pmjay_empanelled`
- `radiology_ct`
- `radiology_mri`
- `radiology_usg`
- `radiology_xray`
- `<specialty>_services` for declared specialties normalized from `specialties` values.

## Additional Coined Terms In Phase 1 Revision

- `accessibility_services`
- `chronic_disease_management`
- `clinical_nutrition`
- `clinical_staff_presence`
- `diabetes_management`
- `emergency_care`
- `fracture_clinic_services`
- `general_healthcare_services`
- `lifestyle_coaching`
- `optical_services`
- `surgery_services`
- `unani_medicine`

## Phase 4 Validator Required Evidence

Forward-looking canonical names referenced as `required_evidence` by rules in
`data/iphs_rules.yaml`. The extractor does not surface these in the current
phase; their absence in any FacilityClaim.capabilities triggers IPHS rule
violations, which is the intended Phase 4 design.

- `ventilator_equipment`
- `radiant_warmer_equipment`
- `pcpndt_certified`
- `power_backup`
- `oxytocin_inventory`
- `cold_chain_equipment`
- `sputum_diagnostic`
- `pediatrics_services`
- `sncu_services`
- `immunisation_services`
- `tb_services`

## Phase 2 Coined Terms

- `aesthetic_dentistry_services`
- `cardiology_services`
- `chest_clinic_services`
- `cosmetology_services`
- `dentoalveolar_surgery_services`
- `dermatology_services`
- `emergency_medicine_services`
- `family_medicine_services`
- `gynecology_and_obstetrics_services`
- `internal_medicine_services`
- `joint_reconstruction_surgery_services`
- `kidney_stone_management`
- `laser_dentistry_services`
- `naturopathy_services`
- `neurology_services`
- `ophthalmology_services`
- `oral_and_maxillofacial_surgery_services`
- `orthodontics_services`
- `orthopedic_sports_medicine_services`
- `orthopedic_surgery_services`
- `pathology_services`
- `prosthodontics_services`
- `pulmonology_services`
- `root_canal_treatment_services`
- `sleep_medicine_services`
