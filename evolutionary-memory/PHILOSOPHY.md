# The Pragmatic Feature-First Philosophy

These guiding principles define the "Way of Working" for all agents and contributors within this project.

### I. Outcome-Driven Engineering
The ultimate metric of code quality is **behavioral correctness**. If the code functions perfectly according to the requirements, it is "good code." Functional utility always outweighs aesthetic perfection.

### II. Tri-Tier Verification
Reliability is enforced through three distinct lenses:
1.  **Automated Tests:** To verify logical correctness.
2.  **User Testing:** To verify that the implementation meets the human intent.
3.  **Performance Audits:** Triggered only when execution latency exceeds acceptable thresholds.

### III. High-Signal Context
Agents perform best with **clear and concise context**. Avoid "Granular Bloat." It is not necessary for every function to be beautifully written; it is only necessary for the logic to be functional, understandable, and traceable.

### IV. Feature-First Focus
We manage the project at the **Product Feature level**. The Librarian tracks the evolution of user-facing capabilities, not the granularity of functions or methods. Our goal is the growth of the product, not the perfection of the machine.
