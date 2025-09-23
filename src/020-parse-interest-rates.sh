#!/usr/bin/env bash

# Script to extract interest rate data from HTML and output as CSV
# Expected input: HTML file containing interest rate table
# Output: CSV format with Date,Currency,TierLow,TierHigh,Rate,BenchmarkDiff

# Print CSV header
echo "Date,Currency,TierLow,TierHigh,Rate,BenchmarkDiff"

# Process the HTML file
awk -v TODAY="$(TZ=US/Eastern date +%F)" '
BEGIN {
    inGlobal = 0
    inTbody = 0
    inRow = 0
    lastCurrency = ""
    row = ""
}

# Enter the section once we see the Global Interest Rates heading
/Global Interest Rates/ { inGlobal = 1 }

# Start of the target table body
inGlobal && /<tbody>/ { inTbody = 1; next }

# End of the target table body (stop capturing)
inTbody && /<\/tbody>/ { inTbody = 0; inGlobal = 0; next }

# Begin a row buffer on <tr>
inTbody && /<tr[^>]*>/ {
    inRow = 1
    row = ""
}

# Accumulate row contents while inside a row
inRow {
    row = row $0 "\n"
}

# When the row closes, parse and emit CSV
inRow && /<\/tr>/ {
    currency = ""
    tier = ""
    rateTxt = ""
    rate = ""
    tierLow = ""
    tierHigh = ""
    bmDiff = ""

    # Normalize row
    gsub(/\r/, "", row)

    # Extract <td>...</td> cells one by one
    pos = 1
    tdcount = 0
    while (1) {
        s = substr(row, pos)
        if (match(s, /<td[^>]*>/) == 0) { break }
        tdStart = pos + RSTART - 1
        contentStart = tdStart + RLENGTH

        s2 = substr(row, contentStart)
        if (match(s2, /<\/td>/) == 0) { break }
        contentEnd = contentStart + RSTART - 2

        cell = substr(row, contentStart, contentEnd - contentStart + 1)

        # Strip tags and clean
        gsub(/<[^>]+>/, "", cell)
        gsub(/&nbsp;/, " ", cell)
        gsub(/^[ \t\r\n]+/, "", cell)
        gsub(/[ \t\r\n]+$/, "", cell)

        tdcount++
        if (tdcount == 1) {
            currency = cell
        } else if (tdcount == 2) {
            tier = cell
        } else if (tdcount == 3) {
            rateTxt = cell
        }

        # Move past this </td>
        pos = contentEnd + 6
    }

    # Carry forward currency when first cell is blank (continuation rows)
    if (currency == "") {
        currency = lastCurrency
    } else {
        lastCurrency = currency
    }

    # Extract numeric rate (first % found), allow negatives
    if (rateTxt != "") {
        if (match(rateTxt, /-?[0-9]+(\.[0-9]+)?%/)) {
            rate = substr(rateTxt, RSTART, RLENGTH)
            gsub(/%/, "", rate)
        } else if (match(rateTxt, /-?[0-9]+(\.[0-9]+)?/)) {
            rate = substr(rateTxt, RSTART, RLENGTH)
        } else {
            rate = ""
        }
    }

    # Extract BenchmarkDiff from "(BM - X%)" if present
    if (rateTxt != "") {
        tmp = rateTxt
        if (match(tmp, /BM[ \t]*-[ \t]*[0-9]+(\.[0-9]+)?%/)) {
            seg = substr(tmp, RSTART, RLENGTH)
            if (match(seg, /[0-9]+(\.[0-9]+)?/)) {
                bmDiff = substr(seg, RSTART, RLENGTH)
            }
        }
    }

    # Parse tier into TierLow and TierHigh (strip commas)
    if (tier != "") {
        t = tier
        # collect up to two numeric values from the tier text
        delete nums
        numsCnt = 0
        rest = t
        while (match(rest, /[0-9][0-9,\.]*/)) {
            num = substr(rest, RSTART, RLENGTH)
            gsub(/,/, "", num)
            numsCnt++
            nums[numsCnt] = num
            rest = substr(rest, RSTART + RLENGTH)
            if (numsCnt == 2) break
        }

        if (tolower(t) == "all") {
            tierLow = ""
            tierHigh = ""
        } else if (index(t, ">") > 0) {
            # e.g., "> 10,000"
            if (numsCnt >= 1) {
                tierLow = nums[1]
                tierHigh = ""
            }
        } else if (index(t, "≤") > 0 || index(t, "<=") > 0 || index(t, "-") > 0) {
            # e.g., "0 ≤ 10,000" or "15,000 ≤ 150,000"
            if (numsCnt == 2) {
                tierLow = nums[1]
                tierHigh = nums[2]
            } else if (numsCnt == 1) {
                tierLow = "0"
                tierHigh = nums[1]
            }
        } else {
            # fallback: single number means lower bound
            if (numsCnt >= 1) {
                tierLow = nums[1]
                tierHigh = ""
            }
        }
    }

    if (currency != "" && rate != "" && tier != "") {
        printf "%s,%s,%s,%s,%s,%s\n", TODAY, currency, tierLow, tierHigh, rate, bmDiff
    }

    inRow = 0
    row = ""
}

'