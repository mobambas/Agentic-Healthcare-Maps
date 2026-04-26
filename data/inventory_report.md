<!-- Phase 1 revision: replaced low-signal gold scaffold records 14b80f2442513a54 (PHC Munambam) -> f595fb439aaf5c0c, 069e379dee0787f3 (Dr. Mane's Lifeline Accident Hospital) -> 96179690c7f34ea8, 8d1179425b9b6145 (Janagama Clinic) -> 8e9fbe59abcf2aa9. -->

# VF Facility Dataset Inventory Report

Phase 1 observation report generated from `data/vf_facilities.csv` using all rows. Completeness treats null-like values (`null`, empty string, and empty list `[]`) as missing.

## Dataset Shape

- Rows: 10,000
- Columns: 41
- Source record key: `sha256(name|zip|lat|lon)[:16]`, matching `agent/schemas/facility.py`.

## Per-Column Completeness

| column | present | missing | completeness |
| --- | --- | --- | --- |
| name | 10000 | 0 | 100.0% |
| phone_numbers | 9998 | 2 | 100.0% |
| officialPhone | 8646 | 1354 | 86.5% |
| email | 6012 | 3988 | 60.1% |
| websites | 10000 | 0 | 100.0% |
| officialWebsite | 4054 | 5946 | 40.5% |
| yearEstablished | 789 | 9211 | 7.9% |
| facebookLink | 9786 | 214 | 97.9% |
| twitterLink | 18 | 9982 | 0.2% |
| linkedinLink | 19 | 9981 | 0.2% |
| instagramLink | 85 | 9915 | 0.9% |
| address_line1 | 10000 | 0 | 100.0% |
| address_line2 | 6566 | 3434 | 65.7% |
| address_line3 | 2664 | 7336 | 26.6% |
| address_city | 10000 | 0 | 100.0% |
| address_stateOrRegion | 10000 | 0 | 100.0% |
| address_zipOrPostcode | 9900 | 100 | 99.0% |
| address_country | 10000 | 0 | 100.0% |
| address_countryCode | 10000 | 0 | 100.0% |
| facilityTypeId | 10000 | 0 | 100.0% |
| operatorTypeId | 5638 | 4362 | 56.4% |
| affiliationTypeIds | 107 | 9893 | 1.1% |
| description | 9061 | 939 | 90.6% |
| numberDoctors | 635 | 9365 | 6.3% |
| capacity | 97 | 9903 | 1.0% |
| specialties | 10000 | 0 | 100.0% |
| procedure | 3398 | 6602 | 34.0% |
| equipment | 1598 | 8402 | 16.0% |
| capability | 6421 | 3579 | 64.2% |
| recency_of_page_update | 530 | 9470 | 5.3% |
| distinct_social_media_presence_count | 6628 | 3372 | 66.3% |
| affiliated_staff_presence | 6476 | 3524 | 64.8% |
| custom_logo_presence | 4564 | 5436 | 45.6% |
| number_of_facts_about_the_organization | 343 | 9657 | 3.4% |
| post_metrics_most_recent_social_media_post_date | 2201 | 7799 | 22.0% |
| post_metrics_post_count | 933 | 9067 | 9.3% |
| engagement_metrics_n_followers | 4474 | 5526 | 44.7% |
| engagement_metrics_n_likes | 3503 | 6497 | 35.0% |
| engagement_metrics_n_engagements | 1332 | 8668 | 13.3% |
| latitude | 10000 | 0 | 100.0% |
| longitude | 10000 | 0 | 100.0% |

## Categorical Value Distributions

### `facilityTypeId`
| value | count | share |
| --- | --- | --- |
| clinic | 6011 | 60.1% |
| hospital | 2789 | 27.9% |
| dentist | 740 | 7.4% |
| doctor | 276 | 2.8% |
| farmacy | 166 | 1.7% |
| pharmacy | 18 | 0.2% |

### `operatorTypeId`
| value | count | share |
| --- | --- | --- |
| private | 5569 | 55.7% |
| <missing> | 4362 | 43.6% |
| public | 69 | 0.7% |

### `address_stateOrRegion`
| value | count | share |
| --- | --- | --- |
| Maharashtra | 1506 | 15.1% |
| Uttar Pradesh | 1058 | 10.6% |
| Gujarat | 838 | 8.4% |
| Tamil Nadu | 630 | 6.3% |
| Kerala | 597 | 6.0% |
| Rajasthan | 495 | 5.0% |
| West Bengal | 483 | 4.8% |
| Karnataka | 455 | 4.5% |
| Delhi | 447 | 4.5% |
| Telangana | 429 | 4.3% |
| Bihar | 429 | 4.3% |
| Haryana | 385 | 3.9% |
| Punjab | 372 | 3.7% |
| Madhya Pradesh | 371 | 3.7% |
| Andhra Pradesh | 276 | 2.8% |
| Jharkhand | 140 | 1.4% |
| Uttarakhand | 136 | 1.4% |
| Assam | 126 | 1.3% |
| Chhattisgarh | 115 | 1.1% |
| Odisha | 109 | 1.1% |
| Jammu And Kashmir | 78 | 0.8% |
| Himachal Pradesh | 48 | 0.5% |
| Tripura | 33 | 0.3% |
| Goa | 32 | 0.3% |
| Punjab Region | 30 | 0.3% |
| Puducherry | 29 | 0.3% |
| Chandigarh | 27 | 0.3% |
| Mumbai | 26 | 0.3% |
| Pune | 18 | 0.2% |
| Manipur | 18 | 0.2% |
| Chennai | 13 | 0.1% |
| Up | 6 | 0.1% |
| Bengaluru | 5 | 0.1% |
| Ernakulam | 5 | 0.1% |
| Mizoram | 5 | 0.1% |
| Sikkim | 5 | 0.1% |
| Thane | 4 | 0.0% |
| Thrissur | 4 | 0.0% |
| Malappuram | 4 | 0.0% |
| Kolkata | 4 | 0.0% |
| Meghalaya | 4 | 0.0% |
| Tamilnadu | 4 | 0.0% |
| Gurugram | 4 | 0.0% |
| Hooghly | 3 | 0.0% |
| Solapur | 3 | 0.0% |
| Ahmedabad | 3 | 0.0% |
| Nagaland | 3 | 0.0% |
| Ludhiana | 3 | 0.0% |
| Navi Mumbai | 3 | 0.0% |
| Beed | 3 | 0.0% |
| New Delhi | 3 | 0.0% |
| Ghaziabad | 3 | 0.0% |
| U.p. | 3 | 0.0% |
| Nagpur | 3 | 0.0% |
| Howrah | 3 | 0.0% |
| Lucknow | 3 | 0.0% |
| Salem | 3 | 0.0% |
| Kochi | 2 | 0.0% |
| Durg | 2 | 0.0% |
| Surat | 2 | 0.0% |
| Kannur | 2 | 0.0% |
| North West Delhi | 2 | 0.0% |
| Mehsana | 2 | 0.0% |
| Patiala | 2 | 0.0% |
| Arunachal Pradesh | 2 | 0.0% |
| Allahabad | 2 | 0.0% |
| Ropar | 2 | 0.0% |
| Jaipur | 2 | 0.0% |
| Pondicherry | 2 | 0.0% |
| Bharuch | 2 | 0.0% |
| Hyderabad | 2 | 0.0% |
| Gaya | 2 | 0.0% |
| Secunderabad | 2 | 0.0% |
| Jammu & Kashmir | 2 | 0.0% |
| Pune, Maharashtra | 2 | 0.0% |
| Kurukshetra | 1 | 0.0% |
| Alappuzha | 1 | 0.0% |
| Birbhum | 1 | 0.0% |
| Ut | 1 | 0.0% |
| Ambernath | 1 | 0.0% |
| Nit | 1 | 0.0% |
| Ayodhya | 1 | 0.0% |
| Amritsar | 1 | 0.0% |
| Ganderbal | 1 | 0.0% |
| Supaul | 1 | 0.0% |
| Ut Of Dadra & Nagar Haveli And Daman Diu | 1 | 0.0% |
| North 24 Parganas | 1 | 0.0% |
| Vellore | 1 | 0.0% |
| Kurnool | 1 | 0.0% |
| Golaghat | 1 | 0.0% |
| Chikmagalur | 1 | 0.0% |
| Kupwara | 1 | 0.0% |
| Jalgaon District | 1 | 0.0% |
| Jodhpur | 1 | 0.0% |
| Gurdaspur | 1 | 0.0% |
| Kalyanpur Kanpur | 1 | 0.0% |
| Silchar | 1 | 0.0% |
| Mukteshwar | 1 | 0.0% |
| Bhilai | 1 | 0.0% |
| Anantnag | 1 | 0.0% |
| Navi Mumbai, Maharashtra | 1 | 0.0% |
| Singrauli | 1 | 0.0% |
| Durgapura | 1 | 0.0% |
| Thiruvananthapuram | 1 | 0.0% |
| Charkhi Dadri, Haryana | 1 | 0.0% |
| Pathanamthitta | 1 | 0.0% |
| Gj | 1 | 0.0% |
| Surendranagar District | 1 | 0.0% |
| Paschim Medinipur | 1 | 0.0% |
| Daman And Diu | 1 | 0.0% |
| Alipurduar | 1 | 0.0% |
| Darrang | 1 | 0.0% |
| Zirakpur | 1 | 0.0% |
| Palakkad | 1 | 0.0% |
| Pune-411044 | 1 | 0.0% |
| National Capital Territory Of Delhi | 1 | 0.0% |
| Pimpri-chinchwad | 1 | 0.0% |
| Murshidabad | 1 | 0.0% |
| Sibsagar | 1 | 0.0% |
| Chattisgarh | 1 | 0.0% |
| Rajsamand, Rajasthan | 1 | 0.0% |
| Belgaum | 1 | 0.0% |
| Bokaro Steel City, Jharkhand | 1 | 0.0% |
| Gautam Buddha Nagar | 1 | 0.0% |
| Tiruvallur-602001 | 1 | 0.0% |
| Sikar | 1 | 0.0% |
| Mohali | 1 | 0.0% |
| Thoothukudi | 1 | 0.0% |
| Dinajpur | 1 | 0.0% |
| Telangana State | 1 | 0.0% |
| Jhajjar | 1 | 0.0% |
| West Tripura | 1 | 0.0% |
| Saran | 1 | 0.0% |
| Karimnagar | 1 | 0.0% |
| Azamgarh | 1 | 0.0% |
| Sector 56 | 1 | 0.0% |
| Guna, Madhya Pradesh | 1 | 0.0% |
| Andhrapradesh | 1 | 0.0% |
| Erode | 1 | 0.0% |
| Churu | 1 | 0.0% |
| Ncr | 1 | 0.0% |
| West Delhi | 1 | 0.0% |
| Udupi | 1 | 0.0% |
| Chittoor | 1 | 0.0% |
| Delhi Division | 1 | 0.0% |
| Nct | 1 | 0.0% |
| Madhyapradesh | 1 | 0.0% |
| Safdarjung Enclave | 1 | 0.0% |
| Malappuram, Kerala | 1 | 0.0% |
| Gandhinagar | 1 | 0.0% |
| Rajkot | 1 | 0.0% |
| Delhi Ncr | 1 | 0.0% |
| J&k | 1 | 0.0% |
| Varanasi | 1 | 0.0% |
| Thanjavur | 1 | 0.0% |
| Pali-rajasthan | 1 | 0.0% |
| Raipur | 1 | 0.0% |
| Mh | 1 | 0.0% |
| Bokaro | 1 | 0.0% |
| Thatipur | 1 | 0.0% |
| Chakdah | 1 | 0.0% |
| Udaipur | 1 | 0.0% |
| Ladakh | 1 | 0.0% |
| Mandamarri | 1 | 0.0% |
| Veraval | 1 | 0.0% |
| Ambedkar Nagar | 1 | 0.0% |
| Jehanabad, Bihar | 1 | 0.0% |
| Kharagpur | 1 | 0.0% |
| Puruliya | 1 | 0.0% |
| Barpeta, Assam | 1 | 0.0% |
| Jabalpur | 1 | 0.0% |
| Aligarh | 1 | 0.0% |
| Chandrapur | 1 | 0.0% |
| Moradabad | 1 | 0.0% |
| Kalyan | 1 | 0.0% |
| Prakasam District | 1 | 0.0% |
| Rajarhat | 1 | 0.0% |
| Nuh | 1 | 0.0% |
| Sangrur | 1 | 0.0% |
| Chittur | 1 | 0.0% |
| Aurangabad-bihar | 1 | 0.0% |
| Durgapur | 1 | 0.0% |
| Mira Bhayander | 1 | 0.0% |
| Bangalore | 1 | 0.0% |
| Rajahmundry | 1 | 0.0% |
| Dhar District, Madhya Pradesh | 1 | 0.0% |
| Chinchwad | 1 | 0.0% |
| Sitamarhi | 1 | 0.0% |
| Dudhani | 1 | 0.0% |
| Khaira | 1 | 0.0% |
| Fatehabad, Haryana | 1 | 0.0% |
| Ka | 1 | 0.0% |
| Uttaranchal | 1 | 0.0% |
| Faizabad | 1 | 0.0% |

## Free-Text Length Statistics

| field | nonempty | min_chars | p25_chars | median_chars | p75_chars | p95_chars | max_chars | mean_chars |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| description | 9061 | 3 | 37 | 82 | 135 | 316 | 3185 | 112.1 |
| specialties | 10000 | 7 | 16 | 28 | 62 | 182 | 733 | 52.7 |
| procedure | 3398 | 1 | 72 | 153 | 341 | 1002 | 5240 | 286.0 |
| equipment | 1598 | 9 | 51 | 78 | 135 | 344 | 1265 | 116.5 |
| capability | 6421 | 6 | 84 | 163 | 332 | 944 | 3555 | 277.0 |

### List Field Item Counts

| field | nonempty | min_items | p25_items | median_items | p75_items | p95_items | max_items | mean_items |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| specialties | 10000 | 1 | 1 | 2 | 3 | 9 | 32 | 2.9 |
| procedure | 3398 | 1 | 2 | 4 | 10 | 29 | 256 | 8.3 |
| equipment | 1598 | 1 | 1 | 2 | 3 | 9 | 42 | 2.9 |
| capability | 6421 | 1 | 2 | 4 | 7 | 18 | 71 | 5.6 |

## Representative Messy Records

### 1. Rural-state hospital with big claims and thin equipment

- `source_record_id`: `dfea6f6217d6b8b3`
- Facility: Criticare Hospital (A Unit Of Criticalcare)
- Type/operator/state: `hospital` / `private` / `Uttar Pradesh`
- Note: Hospital in a rural/underserved state with broad service claims but sparse declared equipment.

| raw field | value |
| --- | --- |
| description | Criticare - The best private hospital in Lucknow |
| specialties | urology | anesthesiology | nephrology | otolaryngology | gastroenterology | internalMedicine | jointReconstructionSurgery | endocrinologyAndDiabetesAndMetabolism | pediatrics | criticalCareMedicine | upperGIAndForegutSurgery | dermatology | gynecologyAndObstetrics | renalTransplantationUrology | oralAndMaxillofacialSurgery | plasticSurgery | neurosurgery | neurology | neonatologyPerinatalMedicine | cardiology | emergencyMedicine | anesthesia | radiology | ophthalmology | orthopedicSurgery | physicalMedicineAndRehabilitation | generalSurgery | pathology | dentistry |
| procedure | Performs joint replacement surgeries | Criticare is a hospital based in Lucknow | Laparoscopic surgery | Performs GI (gastrointestinal) surgeries | Provides dialysis procedures | Kidney transplant |
| equipment | No specific imaging or diagnostic equipment models named in the content | Claims advanced equipment and world-class technology |
| capability | Provides 24x7 emergency care and ambulance services | NABH accredited (entry level) hospital | Has an Advanced Trauma Unit | Has 25+ doctors on staff | Has a Joint Replacement Unit | Described as the best private hospital in Lucknow | Provides Pediatrics & Neonatology services | Kidney transplant program available | Provides 24x7 emergency care | Has a Critical Care Unit | Has a Cardiac Care Unit | Provides Neurosciences | Provides Obstetrics & Gynaecology | Provides Gastroenterology & Gastro Surgery | Has Advanced Trauma & Joint Replacement Unit | Provides Gastroenterology services | Provides nephrology services | Advanced pathology services available 24x7 | Provides Nephrology - Dialysis | Provides Obstetrics & Gynecology services | Private hospital in Lucknow | Provides 24x7 emergenc... |

### 2. Private clinic with multi-specialty claims

- `source_record_id`: `5a001597fb6741a6`
- Facility: Hyderabad Cosmetic Surgery
- Type/operator/state: `clinic` / `private` / `Telangana`
- Note: Private clinic with many specialties/procedures, useful for over-claim risk review.

| raw field | value |
| --- | --- |
| description | Hyderabad Cosmetic Surgery is a private cosmetic and plastic surgery clinic in Hyderabad, India, offering gynecomastia surgery and other cosmetic procedures. |
| specialties | breastSurgery | aestheticAndCosmeticSurgery | dermatology | generalSurgery | familyMedicine | reconstructivePlasticSurgery | woundHealingAndDermatologicRegenerativeMedicine | oralAndMaxillofacialSurgery | plasticSurgery | cosmeticDermatology |
| procedure | Face Lift Surgery (Rhytidectomy) | Keloids & Hypertrophic Scars | Vaginoplasty | Fat Grafting is offered | Face & Neck Rejuvenation is offered | Gynaecomastia Surgery (Male Breast Reduction) | Brachioplasty (Arm Lift) is offered | Congenital Deformities | Laser Skin Treatment | Breast Lift (Mastopexy) | Eyelid Surgery (Blepharoplasty) | Chin Surgery (Mentoplasty) | Pressure Sores | Tropical Plastic Surgery | Endo-Vascular Laser Treatment is offered | Facial Implants are offered | Skin Tag Removal | Mesotherapy | Non-Surgical Nose Job (HA Fillers) | Total Body Lift is offered | Hymenoplasty | Calf Implants are offered | PRP & PRF Injections is offered | Thighplasty (Thigh Lift) | Acne & Trauma Scars (Acne Scar Treatment) | Nipple & Areola Correction is offered | Fat Transfer for Facial S... |
| equipment | <missing> |
| capability | Has performed thousands of aesthetic and reconstructive surgeries across Telangana including Hyderabad | Offers cosmetic surgery (aesthetic surgery) services | Has 13 years of clinical practice | Operates in Hyderabad, Telangana, India | Practice locations include Suvidha Hospitals (Hyderabad, Telangana) | Displays ISAPS affiliation/logo on the site | Provides non-surgical skin treatments including LASER Skin Treatments, PRP & PRF Injections, and Mesotherapy | Dr. Ravindranath Bhyri is a Consultant Plastic, Reconstructive & Aesthetic Surgeon | Procedures are performed in outpatient settings for cosmetic surgery | Offers non-surgical cosmetic procedures in addition to surgical procedures | Operates as a specialized Gynecomastia Centre in Hyderabad | Offers cosmetic surgery and reconstruc... |

### 3. Dental clinic

- `source_record_id`: `cf868c87163acf64`
- Facility: 1000 Smiles Dental Clinic
- Type/operator/state: `clinic` / `null` / `Telangana`
- Note: Dental facility should usually short-circuit out of IPHS ladder validation.

| raw field | value |
| --- | --- |
| description | Dental clinic offering RCT (Root Canal) and Laser Dentistry in Amberpet, Hyderabad. |
| specialties | familyMedicine | periodontics | endodontics | dentistry | aestheticDentistry |
| procedure | Performs root canal therapy (RCT) | Provides laser dentistry services |
| equipment | <missing> |
| capability | Has been in operation for 10 years | Dental clinic |

### 4. Diagnostic center

- `source_record_id`: `36e59b595dc18e17`
- Facility: 7LABS
- Type/operator/state: `clinic` / `private` / `Andhra Pradesh`
- Note: Diagnostics/radiology/pathology record tests non-hospital capability handling.

| raw field | value |
| --- | --- |
| description | Diagnostics centre |
| specialties | pathology | clinicalPathology | familyMedicine |
| procedure | <missing> |
| equipment | <missing> |
| capability | 7LABS is listed on Mediyaar's Guntur labs page as a nearby diagnostic centre | Operates as a diagnostics centre in Guntur, Andhra Pradesh, India | Offers value-added services | 7LABS is a diagnostic laboratory located in SVN Colony, Guntur, Andhra Pradesh | Provides quality diagnosis in testing | 7LABS is listed as a nearby diagnostic centre in Ajay Nagar Mangalagiri, Guntur |

### 5. Pharmacy

- `source_record_id`: `937f4cfc71871233`
- Facility: A2Z Care Pharmacy
- Type/operator/state: `farmacy` / `null` / `West Bengal`
- Note: Pharmacy record should not be scored as IPHS non-compliant facility care.

| raw field | value |
| --- | --- |
| description | We are a brand new retail medicine shop based Noth 24 Parganas in west Bengal. We have well-known specialist Doctors for Cardiology, Gynae & Obs, pediatrics, ENT, Medicine, orthopedic, and 24 hours doctor's support. We have a free home delivery service. |
| specialties | pediatrics | cardiology | otolaryngology | gynecologyAndObstetrics | internalMedicine | orthopedicSurgery |
| procedure | <missing> |
| equipment | <missing> |
| capability | Retail medicine shop | Located in Habra, West Bengal, India | Has specialist doctors for Cardiology, Gynecology & Obstetrics, Pediatrics, ENT, Medicine, and Orthopedics | Provides 24-hour doctor support | Offers free home delivery service | Offers contactless delivery and online booking |

### 6. Null operatorTypeId

- `source_record_id`: `0256bf60033d8abb`
- Facility: 24x7 Family Clinix
- Type/operator/state: `clinic` / `null` / `Uttar Pradesh`
- Note: Operator type is missing, matching a major dataset completeness gap.

| raw field | value |
| --- | --- |
| description | <missing> |
| specialties | familyMedicine |
| procedure | <missing> |
| equipment | <missing> |
| capability | <missing> |

### 7. Hindi or transliterated facility name

- `source_record_id`: `12b44bb334009189`
- Facility: Aarogya Ashirwad Nursing Home
- Type/operator/state: `hospital` / `null` / `Bihar`
- Note: Name contains Hindi/transliterated tokens that may affect fuzzy matching.

| raw field | value |
| --- | --- |
| description | Medical & Surgical Health Centre |
| specialties | internalMedicine |
| procedure | <missing> |
| equipment | <missing> |
| capability | <missing> |

### 8. Smallest non-empty description

- `source_record_id`: `99b1c67a6b1f3667`
- Facility: Royal Diagnostic Center
- Type/operator/state: `clinic` / `private` / `Maharashtra`
- Note: Shortest non-empty description stresses evidence availability and sparse-text handling.

| raw field | value |
| --- | --- |
| description | N/A |
| specialties | familyMedicine |
| procedure | Pathology testing |
| equipment | <missing> |
| capability | Home service up to 5 km | Outpatient diagnostic services | Private diagnostic center | Health package services |

## Gold Label Scaffold Sampling

- Random seed: `42`
- Sampling rule: stratified sample overrides pure seed-42 random sampling to guarantee review coverage across hard facility categories.
- `proposed_labels` are machine-generated best guesses for human review and are not ground truth.

| facility_category | sampled | available_pool |
| --- | --- | --- |
| hospital | 12 | 2789 |
| clinic | 10 | 3559 |
| dental | 4 | 2391 |
| diagnostic | 2 | 772 |
| pharmacy | 1 | 171 |
| single_practitioner | 1 | 266 |

## Phase 1 Observations

- The dataset is dominated by clinics and hospitals, with substantial missingness in operator, doctor count, and capacity fields.
- `procedure`, `equipment`, and `capability` are list-like text fields with uneven density; many records have claims but no corresponding equipment list.
- Non-IPHS categories such as dental, pharmacy, and diagnostics need category-level short-circuiting before validator logic to avoid meaningless compliance flags.
- Several records include strong service claims such as 24/7 care, surgery, blood bank, or specialist care without enough structured staffing/equipment evidence to support them; these are candidates for Phase 2 extraction and Phase 3 calibration, not conclusions from inventory alone.
