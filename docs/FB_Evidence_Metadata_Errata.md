# Additive evidence metadata reconciliation

[machine-checked] Exact method IDs reconstructed from the verified FB5.1 archive show 713 executions and 703 distinct methods. Its ten `tests_c7` methods ran once under inherited regression and again under the combined new-tests runner. The FB5.1 wording “713 distinct” is a count-label error, not a failed test or missing evidence. Preserve the original record and all raw results.

[machine-checked] FB5.3 ran all 703 distinct FB5.1 methods, plus three FB5.2 sustained methods and six FB5.3 continuation methods: 712 distinct methods, none missing. Exact IDs, duplicates and test directories are in `evidence/FB5.4/Method_Inventory_Reconciliation.json`. FB6.2 must compare actual method IDs against this inventory and subsequent accepted inventories, rather than comparing headline totals alone.

[machine-checked] The immutable FB5.2 ZIP contains 79 files and five directory entries, 84 ZIP entries total. The original index's 79 describes the file count. The archive has exactly the committed 3,471,368 bytes and SHA-256 `e3764fcff440aa871353da0aebfdc908b8a413b7d694473b113a5ec8f0ff8dff`. No digest failure occurred. Its entry list is saved in `evidence/FB5.4/FB5.2_Archive_Metadata_Erratum.json`. Use 79 files / 84 entries in future reports; preserve the original index and archive bytes.
