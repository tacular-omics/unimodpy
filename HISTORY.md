# History

## 0.1.0 (2026-03-26)

First release.

* Parse UNIMOD OBO files into typed, frozen dataclasses (`UnimodEntry`, `Specificity`, `NeutralLoss`).
* `UnimodDatabase` with lookup by integer ID, UNIMOD accession string, case-insensitive name, and full-text search.
* `Site`, `Position`, and `Classification` `StrEnum` types for type-safe specificity filtering.
* Elemental composition parsing and Hill-notation ProForma formula generation, including monosaccharide abbreviation expansion and isotope label support.
* `load()` convenience function that reads the bundled OBO with no configuration.
* `download()` to fetch the latest OBO from unimod.org.
* Zero third-party dependencies; requires Python 3.12+.
