# Basic Regex Tips for Coral Search

This guide covers the most common patterns you can use when selecting **"Basic Regex"** from the Coral search menu.

Basic regex (also called BRE - Basic Regular Expressions) is the default mode for `grep` and provides fundamental pattern matching capabilities.

---

## 📌 Special Characters

### 1. **`.` - Match Any Single Character**

```regex
f.le
```
**Matches:** `file`, `fale`, `f9le`, `f le` (any character between 'f' and 'le')

```regex
test.txt
```
**Matches:** `test.txt`, `test1txt`, `testXtxt` (`.` matches any character, not literal period)

---

### 2. **`*` - Match Zero or More of Previous Character**

```regex
go*d
```
**Matches:** `gd`, `god`, `good`, `goood` (zero or more 'o's)

```regex
file.*
```
**Matches:** `file`, `file.txt`, `filename`, `file.backup.tar.gz` (file followed by anything)

---

### 3. **`^` - Match Start of Line**

```regex
^Error
```
**Matches:** Lines that START with "Error"
**Won't match:** "  Error" or "Fatal Error" (must be at very beginning)

```regex
^#
```
**Matches:** Comment lines in config files that start with `#`

---

### 4. **`$` - Match End of Line**

```regex
done$
```
**Matches:** Lines that END with "done"
**Won't match:** "done processing" or "done."

```regex
;$
```
**Matches:** Lines ending with semicolon (useful for code searches)

---

### 5. **`[...]` - Character Class (Match Any One)**

```regex
[aeiou]
```
**Matches:** Any vowel

```regex
[0-9]
```
**Matches:** Any single digit

```regex
[A-Z]
```
**Matches:** Any uppercase letter

```regex
file[0-9]
```
**Matches:** `file0`, `file1`, `file2`, ..., `file9`

---

### 6. **`[^...]` - Negated Character Class**

```regex
[^0-9]
```
**Matches:** Any character that is NOT a digit

```regex
[^aeiou]
```
**Matches:** Any consonant (or non-letter)

---

## 🔍 Common Search Patterns

### 7. **Find Email Addresses (Simple)**

```regex
[A-Za-z0-9._-]*@[A-Za-z0-9.-]*
```
**Matches:** `user@example.com`, `admin@test.org`, `contact_us@website.co.uk`

---

### 8. **Find IP Addresses (Simple)**

```regex
[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*
```
**Matches:** `192.168.1.1`, `10.0.0.255`

---

### 9. **Find Phone Numbers**

```regex
[0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]
```
**Matches:** `555-1234`, `800-5555`

```regex
([0-9][0-9][0-9]) [0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]
```
**Matches:** `(555) 123-4567` (requires escaping parentheses with `\(` and `\)`)

---

### 10. **Find Lines with Specific Word Count**

```regex
^[^ ]* [^ ]* [^ ]*$
```
**Matches:** Lines with exactly 3 words

---

### 11. **Find Duplicate Words**

```regex
\([A-Za-z]*\) \1
```
**Matches:** `the the`, `hello hello` (same word repeated)

---

### 12. **Find Lines Starting with Whitespace**

```regex
^[ 	]
```
**Matches:** Lines that start with spaces or tabs (indented lines)

---

### 13. **Find Lines NOT Starting with Comment**

```regex
^[^#]
```
**Matches:** Lines that don't start with `#` (useful for config files)

---

### 14. **Find Quoted Strings**

```regex
"[^"]*"
```
**Matches:** `"hello"`, `"some text here"` (text between double quotes)

---

### 15. **Find Lines with Specific Length**

```regex
^.\{80\}
```
**Matches:** Lines that are at least 80 characters long (note: `\{` and `\}` are escaped in basic regex)

---

### 16. **Find URLs (Simple)**

```regex
http[s]*://[A-Za-z0-9./-]*
```
**Matches:** `http://example.com`, `https://website.org/path`

---

### 17. **Find Hexadecimal Colors**

```regex
#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]
```
**Matches:** `#FF5733`, `#000000`, `#abc123`

---

### 18. **Find TODO/FIXME Comments**

```regex
^.*TODO
```
**Matches:** Any line containing "TODO"

```regex
^.*FIXME:
```
**Matches:** Lines with "FIXME:" comments

---

### 19. **Find Empty Lines**

```regex
^$
```
**Matches:** Completely empty lines (no characters, not even spaces)

---

### 20. **Find Lines with Trailing Whitespace**

```regex
[ 	]$
```
**Matches:** Lines ending with spaces or tabs (common code quality issue)

---

## ⚠️ Important Notes

1. **Escaping in Basic Regex**: Some characters need backslashes to be special:
   - Use `\(` and `\)` for grouping
   - Use `\{` and `\}` for repetition counts
   - Use `\+` for "one or more"
   - Use `\?` for "zero or one"

2. **Case Sensitivity**: Coral search always uses `-i` flag, so searches are **case-insensitive** by default

3. **Literal Dots**: To match a literal period, escape it: `\.`
   - `file\.txt` matches only "file.txt"
   - `file.txt` matches "file.txt", "fileXtxt", etc.

4. **When to Use Extended Regex**: If you need `|` (OR), `+`, `?`, or easier grouping `()`, switch to **Extended Regex** mode instead

---

## 💡 Quick Reference

| Pattern | Meaning | Example | Matches |
|---------|---------|---------|---------|
| `.` | Any character | `c.t` | cat, cot, c9t |
| `*` | Zero or more | `go*d` | gd, god, good |
| `^` | Start of line | `^Error` | Error: failed |
| `$` | End of line | `done$` | Task done |
| `[abc]` | Any of a, b, c | `[aeiou]` | Any vowel |
| `[^abc]` | Not a, b, or c | `[^0-9]` | Non-digit |
| `[a-z]` | Range | `[A-Z]` | Uppercase |
| `\{n\}` | Exactly n times | `[0-9]\{3\}` | 123 |

---

For more advanced patterns with OR logic (`|`), easier grouping, and quantifiers like `+` and `?`, see [EXTENDED-REGEX-TIPS.md](EXTENDED-REGEX-TIPS.md).
