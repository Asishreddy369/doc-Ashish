def validate_aadhaar(aadhaar_str):
    """
    Validates a 12-digit Aadhaar number using the Verhoeff algorithm.
    """
    aadhaar_str = aadhaar_str.replace(" ", "").replace("-", "")
    if not aadhaar_str.isdigit() or len(aadhaar_str) != 12:
        return False

    # Verhoeff tables
    d = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
        [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
        [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
        [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
        [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
        [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
        [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
        [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
        [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
    ]
    p = [
        [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
        [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
        [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
        [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
        [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
        [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
        [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
    ]

    c = 0
    reversed_aadhaar = aadhaar_str[::-1]
    
    for i, num in enumerate(reversed_aadhaar):
        c = d[c][p[i % 8][int(num)]]
        
    return c == 0


def validate_gstin(gstin_str):
    """
    Validates a 15-character GSTIN using Luhn mod-36.
    """
    gstin_str = gstin_str.upper()
    if len(gstin_str) != 15:
        return False
        
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    
    factor = 1
    sum_val = 0
    check_char = gstin_str[-1]
    
    for char in gstin_str[:-1]:
        if char not in chars:
            return False
        code_point = chars.index(char)
        addend = factor * code_point
        factor = 2 if factor == 1 else 1
        addend = (addend // 36) + (addend % 36)
        sum_val += addend
        
    remainder = sum_val % 36
    check_code = (36 - remainder) % 36
    expected_char = chars[check_code]
    
    return expected_char == check_char
