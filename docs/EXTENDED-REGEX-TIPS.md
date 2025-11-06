# Extended Regex Tips for Coral Search

This guide covers powerful pattern matching when selecting **"Extended Regex"** from the Coral search menu.

Extended regex (ERE - Extended Regular Expressions, using `grep -E`) adds powerful operators and simpler syntax compared to basic regex.

---

## 🚀 Key Advantages Over Basic Regex

1. **`|` - OR operator** (no escaping needed)
2. **`+` - One or more** (no escaping needed)
3. **`?` - Zero or one** (no escaping needed)
4. **`()` - Grouping** (no escaping needed)
5. **`{n,m}` - Repetition** (no escaping needed)

---

## 📌 Extended Regex Special Operators

### 1. **`|` - OR Operator (Alternation)**

```regex
error|warning|critical
```
**Matches:** Lines containing "error" OR "warning" OR "critical"

```regex
\.jpg|\.png|\.gif
```
**Matches:** Image files with .jpg, .png, or .gif extensions

```regex
http|https|ftp
```
**Matches:** Lines with any of these protocols

---

### 2. **`+` - One or More**

```regex
go+d
```
**Matches:** `god`, `good`, `goood` (one or more 'o's, but NOT `gd`)

```regex
[0-9]+
```
**Matches:** `5`, `123`, `9999` (one or more digits, any length number)

```regex
err+or
```
**Matches:** `error`, `errror`, `errrror` (common typo catching)

---

### 3. **`?` - Zero or One (Optional)**

```regex
colou?r
```
**Matches:** Both `color` and `colour` (British/American spelling)

```regex
https?
```
**Matches:** Both `http` and `https`

```regex
files?
```
**Matches:** Both `file` and `files` (optional 's')

---

### 4. **`{n,m}` - Specific Repetition Counts**

```regex
[0-9]{3}
```
**Matches:** Exactly 3 digits: `123`, `999`

```regex
[0-9]{3,5}
```
**Matches:** 3 to 5 digits: `123`, `1234`, `12345`

```regex
[0-9]{3,}
```
**Matches:** 3 or more digits: `123`, `1234`, `123456789`

```regex
[a-z]{5,10}
```
**Matches:** Lowercase words with 5-10 letters

---

### 5. **`()` - Grouping**

```regex
(ha)+
```
**Matches:** `ha`, `haha`, `hahaha` (repeated "ha")

```regex
file(name|path|size)
```
**Matches:** `filename`, `filepath`, `filesize`

```regex
(error|warning): (.+)
```
**Matches:** "error: message" or "warning: message" with any text after colon

---

## 🔍 Powerful Search Patterns

### 6. **Find Multiple Keywords (OR Search)**

```regex
TODO|FIXME|HACK|XXX|NOTE
```
**Matches:** Common code annotation keywords

```regex
bug|issue|problem|error|fail
```
**Matches:** Problem-related terms in logs

---

### 7. **Find Email Addresses**

```regex
[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}
```
**Matches:** `user@example.com`, `admin@test.org`, `contact.name@website.co.uk`

---

### 8. **Find Phone Numbers**

```regex
[0-9]{3}-[0-9]{3}-[0-9]{4}
```
**Matches:** `555-123-4567`, `800-555-9999`

```regex
\(?[0-9]{3}\)?[-. ]?[0-9]{3}[-. ]?[0-9]{4}
```
**Matches:** `(555) 123-4567`, `555-123-4567`, `555.123.4567`, `5551234567`

---

### 9. **Find IP Addresses**

```regex
[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}
```
**Matches:** `192.168.1.1`, `10.0.0.255`, `127.0.0.1`

---

### 10. **Find URLs**

```regex
https?://[A-Za-z0-9./?=_-]+
```
**Matches:** `http://example.com`, `https://site.org/path?query=value`

```regex
(http|https|ftp)://[^ ]+
```
**Matches:** Any URL with http, https, or ftp protocol

---

### 11. **Find Dates**

```regex
[0-9]{4}-[0-9]{2}-[0-9]{2}
```
**Matches:** `2025-11-05`, `2024-01-15` (YYYY-MM-DD format)

```regex
[0-9]{2}/[0-9]{2}/[0-9]{4}
```
**Matches:** `11/05/2025`, `01/15/2024` (MM/DD/YYYY format)

```regex
[0-9]{1,2}-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-[0-9]{4}
```
**Matches:** `5-Nov-2025`, `15-Jan-2024`

---

### 12. **Find Times**

```regex
[0-9]{2}:[0-9]{2}:[0-9]{2}
```
**Matches:** `14:30:45`, `09:05:12` (HH:MM:SS format)

```regex
[0-9]{1,2}:[0-9]{2} ?(AM|PM|am|pm)
```
**Matches:** `2:30 PM`, `11:45AM`, `9:05 pm`

---

### 13. **Find Hexadecimal Colors**

```regex
#[0-9A-Fa-f]{6}
```
**Matches:** `#FF5733`, `#000000`, `#abc123` (6-digit hex colors)

```regex
#[0-9A-Fa-f]{3,6}
```
**Matches:** Both `#FFF` and `#FFFFFF` (3 or 6 digit colors)

---

### 14. **Find Version Numbers**

```regex
[0-9]+\.[0-9]+\.[0-9]+
```
**Matches:** `1.2.3`, `2.0.15`, `10.5.1` (semantic versioning)

```regex
v?[0-9]+\.[0-9]+(\.[0-9]+)?
```
**Matches:** `v1.2`, `2.0`, `v3.1.4` (optional 'v' prefix and patch version)

---

### 15. **Find Function Definitions**

```regex
(function|def|fn) [A-Za-z_][A-Za-z0-9_]*\(
```
**Matches:** Function definitions in JavaScript, Python, Rust

```regex
(public|private|protected)? ?(static)? ?[A-Za-z_]+ [A-Za-z_]+\(
```
**Matches:** Java/C++ method definitions

---

### 16. **Find Import/Include Statements**

```regex
^(import|from|include|require) 
```
**Matches:** Import lines in Python, JavaScript, C++

```regex
(import|require)\(.*\)|from .+ import
```
**Matches:** Various import syntaxes

---

### 17. **Find Variable Assignments**

```regex
(var|let|const) [A-Za-z_][A-Za-z0-9_]* =
```
**Matches:** JavaScript variable declarations

```regex
[A-Za-z_][A-Za-z0-9_]* = .+
```
**Matches:** General assignment statements

---

### 18. **Find Class Definitions**

```regex
(class|interface|struct) [A-Za-z_][A-Za-z0-9_]*
```
**Matches:** Class/interface/struct definitions in various languages

---

### 19. **Find Multiple File Extensions**

```regex
\.(txt|md|pdf|doc|docx)$
```
**Matches:** Files ending with .txt, .md, .pdf, .doc, or .docx

```regex
\.(jpg|jpeg|png|gif|bmp|svg)$
```
**Matches:** Image files

```regex
\.(js|ts|jsx|tsx)$
```
**Matches:** JavaScript/TypeScript files

---

### 20. **Find Log Levels**

```regex
(DEBUG|INFO|WARN|ERROR|FATAL):
```
**Matches:** Log entries with severity levels

```regex
\[(ERROR|WARN|INFO)\]
```
**Matches:** Bracketed log levels like `[ERROR]`

---

## 🎯 Advanced Combined Patterns

### 21. **Find Quoted Strings with Content**

```regex
"[^"]+"
```
**Matches:** `"hello"`, `"some text"` (non-empty quoted strings)

```regex
'[^']+'|"[^"]+"
```
**Matches:** Both single and double quoted strings

---

### 22. **Find Comments**

```regex
(//|#).+
```
**Matches:** Single-line comments in many languages

```regex
/\*.+\*/
```
**Matches:** Multi-line C-style comments (on same line)

---

### 23. **Find Environment Variables**

```regex
\$[A-Z_][A-Z0-9_]*
```
**Matches:** `$PATH`, `$HOME`, `$USER` (shell variables)

```regex
\$\{[A-Za-z_][A-Za-z0-9_]*\}
```
**Matches:** `${VAR_NAME}` (bash variable expansion)

---

### 24. **Find Package Names**

```regex
[a-z0-9-]+@[0-9]+\.[0-9]+\.[0-9]+
```
**Matches:** `package-name@1.2.3` (npm-style packages)

---

### 25. **Find Credit Card Patterns (Test Data)**

```regex
[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}
```
**Matches:** `1234-5678-9012-3456`, `1234567890123456`

---

## 💡 Combining Operators

### 26. **Complex OR with Grouping**

```regex
(error|warning|critical) (in|at|from) (file|line|function)
```
**Matches:** Combinations like "error in file", "warning at line", "critical from function"

---

### 27. **Optional Prefix/Suffix**

```regex
(pre)?fix(ed)?
```
**Matches:** `fix`, `fixed`, `prefix`, `prefixed`

---

### 28. **Repeated Patterns**

```regex
([A-Z][a-z]+[ ]?)+
```
**Matches:** Title Case Words Like This

---

### 29. **Flexible Whitespace**

```regex
word1[ ]+word2
```
**Matches:** "word1 word2", "word1  word2", "word1     word2" (any amount of spaces)

---

### 30. **Word Boundaries**

```regex
\b(test|demo|example)\b
```
**Matches:** Whole words only: "test", not "testing" or "contest"

---

## ⚠️ Important Notes

1. **Case Sensitivity**: Coral search uses `-i` flag, so searches are **case-insensitive** by default

2. **Special Characters**: To match literal special characters, escape them with `\`:
   - Literal dot: `\.` (otherwise `.` matches any character)
   - Literal parenthesis: `\(` or `\)`
   - Literal bracket: `\[` or `\]`
   - Literal pipe: `\|`

3. **Greedy Matching**: Quantifiers (`*`, `+`, `?`) are greedy - they match as much as possible

4. **Line-based**: grep searches line by line, so patterns can't match across multiple lines

---

## 📊 Quick Reference Table

| Operator | Meaning | Example | Matches |
|----------|---------|---------|---------|
| `\|` | OR | `cat\|dog` | cat, dog |
| `+` | One or more | `go+d` | god, good |
| `?` | Zero or one | `colou?r` | color, colour |
| `{n}` | Exactly n | `[0-9]{3}` | 123 |
| `{n,m}` | n to m times | `x{2,4}` | xx, xxx, xxxx |
| `{n,}` | n or more | `x{3,}` | xxx, xxxx, ... |
| `()` | Group | `(ab)+` | ab, abab, ababab |
| `\|` in group | OR in group | `(jpg\|png)` | jpg, png |

---

For simpler literal text searching without regex patterns, use the **"Literal"** search option in Coral.

For basic regex patterns without these extended features, see [BASIC-REGEX-TIPS.md](BASIC-REGEX-TIPS.md).
