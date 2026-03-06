## Assumptions Guidelines

### Assumptions Precision & Logical Independence

- Replace generic statements with physics-specific conditions
- Reference fundamental principles (Maxwell equations, thermodynamics, quantum mechanics)
- Include mathematical constraints (boundary conditions, statistical distributions)
- Use backticks for math: All mathematical expressions in backticks with AsciiMath format
- **CRITICAL: Ensure assumptions are truly independent** - no assumption should be derivable from others

### Logical Independence Check

- ❌ Don't include consequences as assumptions: "Angular momentum is conserved due to central force" when central force is already assumed
- ❌ Don't include derived properties: "The gravitational potential gives rise to elliptical orbits" when this follows from Newton's law
- ❌ Don't mix preconditions with consequences: Put foundational frameworks first, derived properties should be in derivation
- ✅ Each assumption should be a genuinely independent starting point

Example Fix:
- ❌ AI: "The system is in thermal equilibrium"
- ✅ Improved: "The radiation field is in thermal equilibrium at temperature T, meaning the emission and absorption rates are balanced and the energy distribution is time-independent"
