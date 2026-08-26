# Normalized Voucher Contract

Field names may follow your language conventions internally, but the voucher HTTP response must use the JSON names and nesting below.

Fields not present in the source XML may be `null`, an empty string, or omitted consistently. Every array shown below must always be an array, including when it is empty or has one item. Do not convert date, money, quantity, rate, or boolean-like source text unless the contract explicitly asks you to do so.

```json
{
  "source": {
    "importId": "stable-id",
    "contentHash": "lowercase-64-character-sha256-hex",
    "voucherIndex": 0
  },
  "attributes": {
    "VCHTYPE": "Receipt",
    "ACTION": "Create"
  },
  "date": "20260715",
  "voucherType": "Receipt",
  "voucherNumber": "RCP-DEMO-001",
  "partyLedgerName": "Demo Customer",
  "narration": "Sanitized fixture",
  "ledgerEntries": [
    {
      "sourceTag": "ALLLEDGERENTRIES.LIST",
      "ledgerName": "Demo Bank",
      "isDeemedPositive": "No",
      "amount": "1250.00",
      "billAllocations": [
        {
          "name": "INV-DEMO-001",
          "billType": "Agst Ref",
          "amount": "-1250.00"
        }
      ],
      "bankAllocations": [
        {
          "date": "20260715",
          "name": "UTR-DEMO-001",
          "transactionType": "Inter Bank Transfer",
          "amount": "1250.00"
        }
      ],
      "rateDetails": []
    }
  ],
  "inventoryEntries": [
    {
      "sourceTag": "ALLINVENTORYENTRIES.LIST",
      "stockItemName": "Demo Item",
      "isDeemedPositive": "No",
      "actualQty": "2 PCS",
      "billedQty": "2 PCS",
      "rate": "50.00/PCS",
      "amount": "100.00",
      "batchAllocations": [
        {
          "godownName": "Main Location",
          "batchName": "Primary Batch",
          "actualQty": "2 PCS",
          "billedQty": "2 PCS",
          "amount": "100.00"
        }
      ],
      "accountingAllocations": [
        {
          "ledgerName": "Demo Sales",
          "isDeemedPositive": "No",
          "amount": "100.00",
          "rateDetails": [
            {
              "dutyHead": "CGST",
              "rate": "9"
            }
          ]
        }
      ],
      "rateDetails": []
    }
  ],
  "warnings": []
}
```

## Important Ownership Rules

The following are separate values and must never overwrite one another:

| XML owner | Normalized owner |
| --- | --- |
| `ALLLEDGERENTRIES.LIST/AMOUNT` | `ledgerEntries[i].amount` |
| `BILLALLOCATIONS.LIST/AMOUNT` | `ledgerEntries[i].billAllocations[j].amount` |
| `BANKALLOCATIONS.LIST/AMOUNT` | `ledgerEntries[i].bankAllocations[j].amount` |
| `ALLINVENTORYENTRIES.LIST/AMOUNT` | `inventoryEntries[i].amount` |
| `BATCHALLOCATIONS.LIST/AMOUNT` | `inventoryEntries[i].batchAllocations[j].amount` |
| `ACCOUNTINGALLOCATIONS.LIST/AMOUNT` | `inventoryEntries[i].accountingAllocations[j].amount` |
| `RATEDETAILS.LIST/GSTRATE` | The `rateDetails` array owned by its direct parent |

Do not deduplicate child rows merely because their values are equal. Position and parent ownership are part of their identity.

## Field Rules

- `source.importId` must equal the import record returned by the upload endpoint.
- `source.contentHash` must equal the SHA-256 of the exact uploaded bytes.
- `source.voucherIndex` is zero-based source order within the XML document, before optional per-voucher validation removes invalid vouchers.
- `attributes` contains the source `VOUCHER` attributes `VCHTYPE` and `ACTION` when present.
- `date`, `voucherType`, `voucherNumber`, `partyLedgerName`, and `narration` come only from direct `VOUCHER` children.
- Ledger `sourceTag` is exactly `ALLLEDGERENTRIES.LIST` or `LEDGERENTRIES.LIST`.
- Inventory `sourceTag` is exactly `ALLINVENTORYENTRIES.LIST` for the required scope.
- `isDeemedPositive` remains source text such as `Yes` or `No`; it does not rewrite `amount`.
- `amount`, `actualQty`, `billedQty`, `rate`, and rate-detail values remain lossless source strings.
- `warnings` contains warnings specific to that voucher. Import-wide warnings remain available through import details.

Extra JSON fields are allowed when documented, but they must not replace, rename, flatten, or change the meaning of required fields.
