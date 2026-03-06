"""Mock Wikipedia API responses for deterministic testing.

Provides pre-recorded Wikipedia content for various physics topics
to avoid actual API calls during testing.
"""

# Mock response for Newton's Second Law
NEWTONS_SECOND_LAW = """
Newton's second law of motion states that the force acting upon an object is equal to
the mass of the object multiplied by its acceleration. Mathematically expressed as F = ma,
where F is force, m is mass, and a is acceleration.

This law was first formulated by Sir Isaac Newton in his work "Philosophiæ Naturalis
Principia Mathematica" (Mathematical Principles of Natural Philosophy), published in 1687.
It is one of the three laws of motion that form the foundation of classical mechanics.

The second law provides a quantitative description of the changes that a force can produce
on the motion of a body. It states that the time rate of change of the momentum of a body
is equal in both magnitude and direction to the force imposed on it.

The SI unit of force is the newton (N), defined as the force required to give a mass of
one kilogram an acceleration of one meter per second squared.

Applications include analyzing the motion of objects in various contexts, from everyday
phenomena to complex engineering systems. The law is fundamental in understanding dynamics
and is widely used in physics and engineering.

References:
1. Newton, I. (1687). Philosophiæ Naturalis Principia Mathematica.
2. Halliday, D., Resnick, R., & Walker, J. (2013). Fundamentals of Physics.
"""

# Mock response for Special Relativity
SPECIAL_RELATIVITY = """
Special relativity is a physical theory that describes the relationship between space and time.
It was introduced by Albert Einstein in his 1905 paper "On the Electrodynamics of Moving Bodies".

The theory is based on two postulates:
1. The laws of physics are invariant in all inertial frames of reference.
2. The speed of light in vacuum is the same for all observers, regardless of their motion.

Key consequences include time dilation, length contraction, and the equivalence of mass and energy
(E = mc²). The theory revolutionized our understanding of space, time, and causality.

Special relativity replaced Newtonian mechanics for describing fast-moving objects and laid the
groundwork for general relativity, which incorporates gravity.

Historical Context:
- Developed in early 20th century
- Built upon work by Lorentz, Poincaré, and others
- Confirmed by numerous experiments including the Michelson-Morley experiment

References:
1. Einstein, A. (1905). "On the Electrodynamics of Moving Bodies". Annalen der Physik.
2. Lorentz, H. A. (1904). "Electromagnetic phenomena in a system moving with any velocity".
"""

# Mock response for Quantum Mechanics (longer content)
QUANTUM_MECHANICS = """
Quantum mechanics is a fundamental theory in physics that provides a description of the physical
properties of nature at the scale of atoms and subatomic particles. It is the foundation of all
quantum physics including quantum chemistry, quantum field theory, quantum technology, and quantum
information science.

Classical physics, the collection of theories that existed before the advent of quantum mechanics,
describes many aspects of nature at an ordinary (macroscopic) scale, but is not sufficient for
describing them at small (atomic and subatomic) scales. Most theories in classical physics can be
derived from quantum mechanics as an approximation valid at large (macroscopic) scale.

Quantum mechanics differs from classical physics in that energy, momentum, angular momentum, and
other quantities of a bound system are restricted to discrete values (quantization), objects have
characteristics of both particles and waves (wave-particle duality), and there are limits to how
accurately the value of a physical quantity can be predicted prior to its measurement, given a
complete set of initial conditions (the uncertainty principle).

Quantum mechanics arose gradually from theories to explain observations which could not be
reconciled with classical physics, such as Max Planck's solution in 1900 to the black-body
radiation problem, and the correspondence between energy and frequency in Albert Einstein's
1905 paper which explained the photoelectric effect. These early attempts to understand
microscopic phenomena, now known as the "old quantum theory", led to the full development
of quantum mechanics in the mid-1920s by Niels Bohr, Erwin Schrödinger, Werner Heisenberg,
Max Born and others. The modern theory is formulated in various specially developed
mathematical formalisms. In one of them, a mathematical function, the wave function,
provides information about the probability amplitude of position, momentum, and other
physical properties of a particle.

Historical Development:
- 1900: Planck introduces quantum hypothesis
- 1905: Einstein explains photoelectric effect
- 1913: Bohr model of the atom
- 1925-1926: Modern quantum mechanics developed (Heisenberg, Schrödinger, Dirac)
- 1927: Copenhagen interpretation formulated

Key Principles:
- Wave-particle duality
- Uncertainty principle
- Quantum superposition
- Quantum entanglement
- Measurement and observation effects

Applications include semiconductor physics, nuclear physics, atomic physics, molecular physics,
quantum chemistry, particle physics, quantum optics, and quantum computing.

References:
1. Planck, M. (1900). "On the Theory of the Energy Distribution Law of the Normal Spectrum".
2. Einstein, A. (1905). "On a Heuristic Point of View about the Creation and Conversion of Light".
3. Bohr, N. (1913). "On the Constitution of Atoms and Molecules".
4. Heisenberg, W. (1927). "Über den anschaulichen Inhalt der quantentheoretischen".
5. Schrödinger, E. (1926). "An Undulatory Theory of the Mechanics of Atoms and Molecules".
"""

# Mock response for 404 (page not found)
NOT_FOUND_RESPONSE = {"error": "Page not found", "status": 404}

# Mock response with very long content (for truncation testing)
VERY_LONG_CONTENT = "A" * 15000 + " This content is way too long and should be truncated. " + "B" * 5000

# Mapping of topics to their mock responses
MOCK_RESPONSES = {
    "Newton's Second Law": NEWTONS_SECOND_LAW,
    "Special Relativity": SPECIAL_RELATIVITY,
    "Quantum Mechanics": QUANTUM_MECHANICS,
    "Nonexistent Topic": NOT_FOUND_RESPONSE,
    "Very Long Topic": VERY_LONG_CONTENT,
    "Hooke's Law": """Hooke's law is a principle of physics that states that the force needed to
extend or compress a spring by some distance is proportional to that distance. The law is named
after 17th-century British physicist Robert Hooke. He first stated the law in 1676 as a Latin
anagram and published the solution in 1678 as "ut tensio, sic vis" which means "as the extension,
so the force" or "the extension is proportional to the force".""",
    "Maxwell's Equations": """Maxwell's equations are a set of coupled partial differential equations
that, together with the Lorentz force law, form the foundation of classical electromagnetism,
classical optics, and electric circuits. The equations provide a mathematical model for electric,
optical, and radio technologies, such as power generation, electric motors, wireless communication,
lenses, radar, etc. Formulated by James Clerk Maxwell in the 1860s.""",
}


def get_mock_wikipedia_content(topic: str) -> str:
    """Get mock Wikipedia content for a given topic.

    Args:
        topic: The physics topic to get content for

    Returns:
        Mock Wikipedia content as a string

    Raises:
        KeyError: If topic not found in mock responses
    """
    if topic in MOCK_RESPONSES:
        response = MOCK_RESPONSES[topic]
        if isinstance(response, dict) and "error" in response:
            raise ValueError(f"Wikipedia page not found: {topic}")
        return response
    raise KeyError(f"No mock response for topic: {topic}")
