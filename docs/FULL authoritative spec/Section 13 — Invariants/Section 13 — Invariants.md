# **SECTION 13 — INVARIANTS (MUST NEVER CHANGE)**  
**Authoritative Specification — Permanent System Rules**  
**Document ID:** Section 13 — Invariants  
**Version:** V0.00  

---

# **13.1 Purpose of This Section**  
This section defines the **permanent, non‑negotiable rules** that govern the entire system.  
These rules must remain true **forever**, regardless of:

- new features  
- future‑phase expansions  
- UI redesigns  
- workflow changes  
- metadata changes  
- asset changes  

These invariants protect the system from drift, corruption, and inconsistency.

---

# **13.2 Metadata Invariants**  
- TMDB is the authoritative metadata source  
- Trakt may only supplement, never override  
- TVMaze may only fill gaps  
- OMDb may only enrich  
- Schema must never drift  
- Required fields must always exist  
- Metadata must always be deterministic  
- Metadata must always be normalized  

---

# **13.3 Asset Invariants**  
- All assets must be local  
- No remote URLs may be used  
- Directory structure must never change  
- Naming conventions must never change  
- Fallback assets must always exist  
- Asset dimensions must remain consistent  
- Asset references must always be valid  

---

# **13.4 Workflow Invariants**  
- Workflows must be deterministic  
- Workflows must never corrupt data  
- Workflows must never introduce partial updates  
- Workflows must always produce human‑readable reports  
- Workflows must never silently modify versions  

---

# **13.5 Script Invariants**  
- Scripts must never overwrite authoritative fields incorrectly  
- Scripts must never delete data without replacement  
- Scripts must never introduce schema drift  
- Scripts must never produce inconsistent metadata  
- Scripts must never modify assets outside their scope  

---

# **13.6 UI Invariants**  
- DPAD navigation must always be deterministic  
- Focus must always be visible  
- Popups must always trap focus  
- Layout must never shift  
- High contrast must always be supported  
- Fallback assets must always render correctly  

---

# **13.7 Error Handling Invariants**  
- Errors must never break the UI  
- Errors must always be logged  
- Errors must always be recoverable  
- Errors must never corrupt metadata  
- Errors must never corrupt assets  

---

# **13.8 System‑Wide Invariants**  
- Determinism is mandatory  
- Reproducibility is mandatory  
- Schema stability is mandatory  
- Local‑only assets are mandatory  
- No silent failures  
- No silent version changes  
- No destructive operations without replacement  

These invariants define the core identity of the system.

---

# **13.9 End of Section 13 — Invariants (Must Never Change)**
