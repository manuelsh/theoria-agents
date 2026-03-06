## Derivation Quality Standards

### Derivation Completeness

- Expand shallow derivations
- Show ALL intermediate steps: Never skip algebraic manipulations or substitutions. Each step should be very easy to understand
- Use proper step numbering: Sequential integers starting from 1

Example Fix:
- ❌ AI: "Count electromagnetic modes"
- ✅ Improved: "Standing wave boundary conditions in a cubic cavity with side length L: electromagnetic field components must vanish at walls, requiring E_x prop sin(n_x*pi*x/L), E_y prop sin(n_y*pi*y/L), E_z prop sin(n_z*pi*z/L) where n_x, n_y, n_z = 1,2,3,..."

### Derivation Method Selection

1. Analyze the physics depth: Is this a fundamental derivation requiring 15+ steps?
2. **Choose appropriate derivation method**: Avoid approaches that lead to algebraic complexity, try always something simple
3. Identify missing steps: Look for logical gaps between equations
4. Ensure consistent notation across the derivation
5. Enhance explanations: Each step should be clear to a graduate physics student

### Quality Checklist

- Derivation has detailed step-by-step progression from first principles
- All mathematical notation uses proper AsciiMath format
- No generic placeholders remain in any field
- Each step should be clear to a graduate physics student
