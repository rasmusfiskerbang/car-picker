# FindLeasing private-provider universe — 20 July 2026

Version: 1.0.0
Capture date: 2026-07-20
Capture completion timestamp: 2026-07-20 21:03:10 +02:00 (surviving capture directory modification time)

## Purpose and authority

This is the **authoritative frozen provider universe for the 20 July 2026 source-access research**. It preserves only the minimum derived discovery data needed to reproduce the provider-assessment register: provider ID, canonical source name, and count of private-filtered records. It deliberately contains no offer/listing documents, vehicle facts, prices, or offer URLs.

FindLeasing is discovery-only here and is **not an authorized offer source**. The raw listing documents are intentionally not committed because the earlier research identified FindLeasing access/reuse restrictions. This manifest must never be used to acquire, enrich, display, or republish offers.

## Capture provenance and deterministic derivation

- Source endpoint identity: `https://backend.findleasing.nu/api/v2/listings/?ownership=0&page=<1..45>&page_size=100` (45 captured pages).
- Raw-capture aggregate: 4,495 listing records; 98 distinct provider IDs.
- Concatenated raw-capture SHA-256: `0ffbaa572aee84900b9185c098866a031014eeee8ddce1abc7f949e3b69c9f34`.
- Raw documents: intentionally not committed; this manifest is the retained minimal derivative.
- Canonicalization: read each captured listing’s `dealer.id` and `dealer.name`; group records by `dealer.id`; retain the exact captured `dealer.name` as the canonical name; count records per ID; sort ascending by numeric provider ID. No live endpoint response was used.
- Manifest totals: 98 rows and 4,495 records.
- Manifest canonical-row SHA-256: `c1c4e98d6dad41d95bfe07daabc2af3732c54cc24d3103883d687e4b07e1820f`, calculated from the UTF-8, LF-terminated canonical serialization `provider_id,canonical_name,private_filtered_record_count\n` followed by the 98 sorted CSV rows. This is the manifest data checksum (not a checksum of raw documents).

## Manifest rows

| Provider ID | Canonical provider name | Private-filtered records |
| ---: | --- | ---: |
| 10 | Nordic Leasing A/S | 23 |
| 39 | FLEXTO A/S | 47 |
| 45 | Hammer-Høyer Biler A/S | 48 |
| 61 | BEKA AUTO A/S | 30 |
| 80 | STARMARK | 18 |
| 95 | Punkt Leasing A/S | 29 |
| 125 | Carlounge Aarhus ApS | 16 |
| 128 | RAF Motors A/S | 24 |
| 213 | AUTOTEKNIKA A/S | 5 |
| 249 | SmartDrive.dk | 26 |
| 270 | Rørbæk Leasing A/S | 37 |
| 276 | MATCHLEASE A/S | 3 |
| 283 | CG Autoteknik | 4 |
| 304 | Cito Car Lease A/S | 16 |
| 338 | Agilease A/S | 102 |
| 345 | Lokal Leasing A/S | 54 |
| 346 | Autohauz Leasing | 1 |
| 368 | Sand Jensen Automobiler A/S | 45 |
| 376 | Midt Leasing A/S | 10 |
| 388 | Vestjysk Bilhus A/S | 5 |
| 415 | Løvborg Biler | 50 |
| 434 | Clevr Car Leasing | 259 |
| 436 | Nordens Biler | 9 |
| 448 | Tørring Auto A/S | 284 |
| 473 | Poul Nielsen Automobiler | 3 |
| 512 | AutoWise ApS | 50 |
| 521 | Complet Leasing A/S | 49 |
| 523 | Globus Biler A/S | 12 |
| 526 | MotorPower ApS | 29 |
| 534 | MB Group | 65 |
| 535 | Fjordlund Bilhus A/S | 26 |
| 539 | Hangaard Biler ApS | 9 |
| 542 | City Leasing ApS | 55 |
| 543 | Fleasing | 153 |
| 545 | Hyrup & Nielsen Pre-Owned ApS | 11 |
| 553 | TA Biler ApS | 11 |
| 582 | Kraft Biler A/S Fredericia | 40 |
| 605 | HT Auto | 1 |
| 613 | P. Christensen A/S | 2 |
| 620 | Jacon Biler A/S | 52 |
| 623 | Flexlease.nu A/S Viby | 4 |
| 640 | Dit Autocenter ApS | 134 |
| 643 | Lokal Leasing A/S | 33 |
| 647 | Olivers Bilcenter A/S | 3 |
| 674 | Linderoth | 33 |
| 676 | WELEASE APS | 29 |
| 677 | Allan Hansen Automobiler | 71 |
| 689 | Car Performance | 22 |
| 690 | Signal Leasing A/S | 13 |
| 698 | Gunner Due Biler | 29 |
| 706 | Forza Leasing Frederikssund | 43 |
| 712 | CORE Leasing A/S | 28 |
| 717 | PR-Cars ApS | 16 |
| 719 | Bayern Autogroup A/S | 460 |
| 720 | P. Christensen | 2 |
| 723 | Bespoke Cars | 5 |
| 725 | Toftegaard Biler | 29 |
| 730 | Terminalen | 255 |
| 735 | Dansk Bilimport | 140 |
| 736 | Gørløse Autoimport | 11 |
| 739 | Ejner Hessel | 2 |
| 759 | Krabbe Invest Handel | 15 |
| 798 | M3 AUTO LEASING | 16 |
| 809 | Car Deal ApS | 34 |
| 813 | Car Vendor ApS | 27 |
| 815 | Tønder Bilcentrum ApS | 38 |
| 821 | Flexlease.nu A/S Odense | 2 |
| 833 | Bertelsen Leasing ApS | 634 |
| 834 | Langsø Biler Silkeborg ApS | 2 |
| 839 | Car Choice ApS | 13 |
| 845 | CARWINE | 5 |
| 856 | MQM BILER ApS | 1 |
| 859 | Autocompany ApS | 13 |
| 860 | Simple Leasing A/S | 35 |
| 864 | AROS LEASING A/S | 97 |
| 865 | Nordic Carhouse ApS | 16 |
| 871 | Bilvejledning.dk ApS | 17 |
| 873 | GranTurismo Cars A/S | 35 |
| 879 | Desko Leasing ApS | 36 |
| 883 | Carventure ApS | 12 |
| 884 | Bilgruppen ApS | 29 |
| 887 | Avibiler ApS | 1 |
| 888 | TS Motors ApS | 130 |
| 890 | Aksel.nu ApS | 13 |
| 893 | Albæk Automobiler ApS | 6 |
| 895 | DANLEASING | 19 |
| 897 | NEW MOBILITY ApS | 11 |
| 901 | Nova Motors ApS | 20 |
| 902 | CAP Leasing ApS | 21 |
| 903 | G.R. BILER, SKIVE A/S | 15 |
| 906 | Schelde Leasing ApS | 29 |
| 908 | Viborg Autohandel ApS | 2 |
| 909 | Smart Autohus ApS | 19 |
| 910 | Kloster Biler ApS | 4 |
| 912 | OJA Biler ApS | 1 |
| 914 | eCAR A/S | 11 |
| 917 | Damkjers Biler ApS | 2 |
| 918 | Bredebro Automobiler ApS | 39 |

## Integrity boundary

This versioned derivative makes the exact provider universe reproducible from this repository while respecting the decision not to retain the raw FindLeasing listing corpus. The raw-capture hash identifies the source material used at derivation time, but does not grant access or reuse permission. Any future change to the universe requires a new versioned manifest, a new capture provenance record, and a new canonical-row checksum.
