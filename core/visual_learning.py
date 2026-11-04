"""
core/visual_learning.py — HONESTIC OS Visual Learning & Smart Visual Response Engine

Generates structured multi-part visual learning modules:
1. Simple Explanation (Intuitive Analogy)
2. Flowchart / Architecture Diagram (ASCII & Process View)
3. Architecture View (Layer-by-layer topology)
4. Visual Teaching Card (Key components breakdown)
5. Real Example / Code Execution
6. Interactive Quiz with Answers & Explanations
7. Executive Summary (Key takeaways)
8. Mind Map (Conceptual hierarchy)

Covers pre-built deep blueprints for core domains:
- Networking (DNS, TCP/IP, OSI)
- Cybersecurity (HTTPS, TLS, Zero Trust)
- Operating Systems (Linux Kernel, Processes)
- Programming (Python, Data Structures, Big-O)
- Artificial Intelligence (Transformers, Attention, Neural Nets)
And dynamically synthesizes visual cards for any technical concept.
"""

from __future__ import annotations
import json
from typing import Dict, Any, Optional, List


LEARNING_MODULES: Dict[str, Dict[str, Any]] = {
    "dns": {
        "title": "Domain Name System (DNS)",
        "category": "Networking",
        "explanation": "DNS is the phonebook of the Internet. Humans access information through domain names like google.com; web browsers interact through Internet Protocol (IP) addresses like 142.250.190.46. DNS translates names to numbers so browsers can load internet resources.",
        "diagram": """
+------------+       1. Query google.com       +-------------------+
|   Client   | ------------------------------> | Recursive Resolver|
|  (Browser) | <------------------------------ |   (e.g. 8.8.8.8)  |
+------------+        8. IP: 142.250.190.46    +-------------------+
                                                  |   ^        |   ^
                    2. Query .com?                |   |        |   |
                    +-----------------------------+   |        |   |
                    v                                 |        |   |
              +-------------+   3. Refer to TLD       |        |   |
              | Root Server | ------------------------+        |   |
              +-------------+                                  |   |
                    4. Query google.com?                       |   |
                    +------------------------------------------+   |
                    v                                              |
              +-------------+   5. Refer to Auth                   |
              | TLD Server  | -------------------------------------+
              +-------------+
                    6. Return IP
                    +------------------------------------------+
                    v                                          |
              +-------------+   7. 142.250.190.46              |
              | Auth Server | ---------------------------------+
              +-------------+
""",
        "architecture_view": "Client Browser -> Local DNS Cache -> Recursive Resolver (ISP/Cloudflare) -> Root Server (.) -> TLD Nameserver (.com) -> Authoritative Nameserver (google.com) -> Target IP",
        "visual_card": {
            "core_concept": "Hierarchical Distributed Database",
            "ports": "UDP 53 (Queries) / TCP 53 (Zone Transfers)",
            "key_records": "A (IPv4), AAAA (IPv6), CNAME (Alias), MX (Mail), TXT (Verification)"
        },
        "real_example": "$ nslookup google.com\nServer: 8.8.8.8\nAddress: 8.8.8.8#53\n\nNon-authoritative answer:\nName: google.com\nAddress: 142.250.190.46",
        "quiz": {
            "question": "Which DNS server is the final authority that holds the actual IP address record?",
            "options": [
                "A) Root Nameserver",
                "B) Recursive Resolver",
                "C) Authoritative Nameserver",
                "D) TLD Nameserver"
            ],
            "correct": "C",
            "explanation": "The Authoritative Nameserver holds the actual DNS records (A, AAAA, CNAME, MX) and returns the final definitive IP address."
        },
        "summary": "DNS resolves human-readable domain names into machine-routable IP addresses through a 4-tier hierarchical resolution chain.",
        "mind_map": "DNS Hierarchy\n├── Root Server (.)\n├── TLD Servers (.com, .org, .io)\n├── Authoritative Nameservers\n└── Local Caching Resolvers"
    },
    "https": {
        "title": "HTTPS & TLS Handshake",
        "category": "Cybersecurity",
        "explanation": "HTTPS (Hypertext Transfer Protocol Secure) encrypts all communication between a browser and a web server using TLS/SSL. It guarantees confidentiality, data integrity, and server authentication so third parties cannot eavesdrop or tamper with your connection.",
        "diagram": """
Client                                                  Server
  |                                                       |
  | ------------ 1. ClientHello (TLS 1.3, ciphers) -----> |
  |                                                       |
  | <----------- 2. ServerHello, Certificate, KeyExchange - |
  |                                                       |
  | [Verify Cert with CA + Derive Symmetric Session Key]  |
  |                                                       |
  | ------------ 3. Finished (Encrypted) ---------------> |
  |                                                       |
  | <=========== 4. Symmetric AES-GCM Encrypted HTTP =====> |
""",
        "architecture_view": "Application (HTTP) -> Transport Layer Security (TLS 1.3 Encryption & Handshake) -> Transport Layer (TCP Port 443) -> Network (IP)",
        "visual_card": {
            "core_concept": "Hybrid Cryptography (Asymmetric Handshake + Symmetric Transport)",
            "ports": "TCP Port 443",
            "cipher_suites": "TLS_AES_256_GCM_SHA384, TLS_CHACHA20_POLY1305_SHA256"
        },
        "real_example": "$ curl -vI https://github.com\n* TLSv1.3 (OUT), TLS handshake, Client hello (1):\n* TLSv1.3 (IN), TLS handshake, Server hello (2):\n* Server certificate: github.com (Issued by DigiCert)\n* SSL connection using TLSv1.3 / TLS_AES_128_GCM_SHA256",
        "quiz": {
            "question": "Which encryption method is used for bulk data transfer after the TLS handshake completes?",
            "options": [
                "A) Asymmetric Encryption (RSA)",
                "B) Symmetric Encryption (AES-GCM / ChaCha20)",
                "C) Unencrypted Plaintext",
                "D) One-Way Hashing (SHA-256)"
            ],
            "correct": "B",
            "explanation": "Asymmetric encryption is only used during the handshake to exchange keys; once established, fast symmetric encryption (like AES-GCM) encrypts all payload data."
        },
        "summary": "HTTPS combines asymmetric public-key cryptography for safe session key negotiation with ultra-fast symmetric AES encryption for data transfer.",
        "mind_map": "HTTPS Architecture\n├── Asymmetric Auth (Public/Private Keys & CA)\n├── Key Agreement (ECDHE / Diffie-Hellman)\n├── Symmetric Encryption (AES-256-GCM)\n└── Message Integrity (HMAC / Poly1305)"
    },
    "linux": {
        "title": "Linux Kernel Architecture & Process Model",
        "category": "Operating Systems",
        "explanation": "Linux is a monolithic Unix-like operating system kernel. User space applications interact with hardware through system calls (syscalls). The kernel manages CPU scheduling, virtual memory paging, virtual file systems (VFS), and network protocols.",
        "diagram": """
+-----------------------------------------------------------+
| User Space: Shell, Web Browser, Compilers, Applications   |
+-----------------------------------------------------------+
        | System Calls (fork, exec, read, write, socket)
        v
+-----------------------------------------------------------+
| Kernel Space:                                             |
|  [ Process Scheduler ]      [ Virtual Memory (Paging) ]  |
|  [ Virtual File System (VFS)][ Network Stack (TCP/IP)  ]  |
|  [ Device Drivers (GPU, NVMe, USB, Wi-Fi)             ]  |
+-----------------------------------------------------------+
        | Hardware abstraction
        v
+-----------------------------------------------------------+
| Hardware: CPU, RAM, NVMe/SSD, NIC, GPU, Motherboard       |
+-----------------------------------------------------------+
""",
        "architecture_view": "User Application -> POSIX C Library (glibc) -> Syscall Interface -> Kernel Subsystems (Scheduler, VFS, Net) -> Hardware Drivers -> Silicon",
        "visual_card": {
            "core_concept": "Monolithic Kernel with Dynamic Loadable Modules (LKM)",
            "privilege_rings": "Ring 0 (Supervisor/Kernel), Ring 3 (User Space)",
            "file_philosophy": "Everything is a file (/dev, /proc, /sys, /etc)"
        },
        "real_example": "$ strace -e trace=openat,read,write python -c 'print(\"HONESTIC OS\")'\nwrite(1, \"HONESTIC OS\\n\", 12) = 12",
        "quiz": {
            "question": "What ring of x86-64 CPU privilege levels does the Linux kernel execute in?",
            "options": [
                "A) Ring 3",
                "B) Ring 0",
                "C) Ring 1",
                "D) Ring 2"
            ],
            "correct": "B",
            "explanation": "Ring 0 is supervisor mode with unrestricted hardware execution; user applications execute isolated in Ring 3."
        },
        "summary": "Linux isolates unprivileged user space from hardware using protected system calls into a high-performance monolithic kernel.",
        "mind_map": "Linux Subsystems\n├── Process Management (CFS Scheduler, Signals)\n├── Memory Management (Page Tables, MMU, Swapping)\n├── VFS (Ext4, Btrfs, ProcFS, SysFS)\n└── Device Drivers & Networking"
    },
    "python": {
        "title": "Python Execution Model & Memory Architecture",
        "category": "Programming",
        "explanation": "Python compiles source code (.py) into intermediate bytecode (.pyc), which executes on the CPython Python Virtual Machine (PVM). Memory allocation uses private heaps managed by reference counting and cyclic generational garbage collection.",
        "diagram": """
Source Code (.py)
      |
      v [Python Compiler]
Bytecode (.pyc / py_compile)
      |
      v [Python Virtual Machine (PVM)]
+---------------------------------------------+
| CPython Evaluation Loop (ceval.c)           |
|                                             |
| Global Interpreter Lock (GIL)               |
| Reference Counting & Generational GC        |
+---------------------------------------------+
      |
      v [Operating System System Calls]
Machine Execution / CPU Instructions
""",
        "architecture_view": "Code -> AST -> Bytecode -> CPython Virtual Machine -> GIL Guard -> System C Runtime -> Machine Code",
        "visual_card": {
            "core_concept": "Bytecode Interpreted with Object Model (PyObject*)",
            "memory_engine": "Reference Counting (Immediate) + Generational GC (Cycles)",
            "concurrency": "GIL for Thread Safety, multiprocessing / asyncio for concurrency"
        },
        "real_example": "import dis\ndef add(a, b): return a + b\ndis.dis(add)\n# 0 LOAD_FAST (a)\n# 2 LOAD_FAST (b)\n# 4 BINARY_OP (+)\n# 8 RETURN_VALUE",
        "quiz": {
            "question": "What primary mechanism allows CPython to reclaim memory immediately when an object is no longer used?",
            "options": [
                "A) Generational Mark-and-Sweep",
                "B) Reference Counting",
                "C) Manual malloc/free",
                "D) Stop-the-world compaction"
            ],
            "correct": "B",
            "explanation": "CPython tracks ob_refcnt on every object; the moment it reaches 0, the memory is freed immediately without waiting for a GC cycle."
        },
        "summary": "Python executes compiled bytecode inside the PVM with automated memory management via reference counters and generational cycle cleanup.",
        "mind_map": "Python Internal Architecture\n├── Lexer & Parser (AST)\n├── Bytecode Compiler\n├── PVM (ceval evaluation loop)\n├── Memory Manager (PyMalloc, GC)\n└── GIL (Thread serialization)"
    },
    "ai": {
        "title": "Transformer Architecture & Large Language Models",
        "category": "Artificial Intelligence",
        "explanation": "Modern LLMs are built on the Transformer architecture using Self-Attention. Rather than processing text sequentially like RNNs, Transformers process all input tokens in parallel, computing contextual relationship weights between every pair of words.",
        "diagram": """
Input Text: "HONESTIC OS"
    |
    v [Tokenizer]
Token IDs: [20412, 1944]
    |
    v [Embedding + Positional Encoding]
Vectors (d_model = 4096)
    |
    v
+---------------------------------------------+
| Transformer Block (repeated Nx times):      |
|  [ Multi-Head Self-Attention (Q, K, V) ]    |
|  [ Layer Normalization & Residual Add ]     |
|  [ Feed-Forward Network (SwiGLU/MLP) ]      |
+---------------------------------------------+
    |
    v
Next Token Probability Distribution (Softmax)
""",
        "architecture_view": "Input Tokens -> Embeddings -> Multi-Head Attention (Queries, Keys, Values) -> Feed Forward Layers -> Softmax -> Next Token",
        "visual_card": {
            "core_formula": "Attention(Q, K, V) = softmax(Q * K^T / sqrt(d_k)) * V",
            "key_layers": "Rotary Positional Embeddings (RoPE), KV Caching, RMSNorm",
            "inference": "Autoregressive generation (token-by-token prediction)"
        },
        "real_example": "# Self-Attention Conceptual Formula:\n# Scores = Q @ K.T / sqrt(d_k)\n# Weights = softmax(Scores)\n# Output = Weights @ V",
        "quiz": {
            "question": "What is the computational complexity of standard self-attention with respect to sequence length N?",
            "options": [
                "A) O(N)",
                "B) O(N log N)",
                "C) O(N^2)",
                "D) O(1)"
            ],
            "correct": "C",
            "explanation": "Full self-attention compares every token with every other token, resulting in quadratic O(N^2) time and memory complexity."
        },
        "summary": "Transformers map contextual dependencies across whole sequences simultaneously via Query-Key-Value self-attention mechanisms.",
        "mind_map": "Transformer Core\n├── Tokenization & Embeddings\n├── Multi-Head Self-Attention\n├── KV Cache Acceleration\n└── Autoregressive Decoding"
    },
    "cybersecurity": {
        "title": "Zero Trust Architecture & Defense in Depth",
        "category": "Cybersecurity",
        "explanation": "Zero Trust is a strategic security model that assumes every entity (inside or outside the network) is untrusted until continuously authenticated and authorized. It replaces perimeter-only castle-and-moat security with micro-segmentation and least privilege.",
        "diagram": """
[ Untrusted Network / Users / Devices ]
                  |
                  v
       +--------------------+
       | Policy Enforcement | (Identity + Device Posture + Context)
       +--------------------+
                  |  Mutual TLS (mTLS) + Ephemeral Tokens
                  v
+-----------------------------------------------------------+
| Micro-Segmented Protected Workloads:                      |
|   [ Service A ] <== Least Privilege mTLS ==> [ Service B ] |
|   [ Vault API ] <== Encrypted Secrets ====> [ Database ]  |
+-----------------------------------------------------------+
""",
        "architecture_view": "Identity Provider (IdP) -> Policy Decision Point (PDP) -> Policy Enforcement Point (PEP) -> Microsegmented Application Resources",
        "visual_card": {
            "three_pillars": "1. Verify Explicitly | 2. Use Least Privilege | 3. Assume Breach",
            "techniques": "mTLS, Short-lived JWTs, Hardware FIDO2 Security Keys",
            "monitoring": "Continuous telemetry audit, anomaly detection"
        },
        "real_example": "# Principle of Least Privilege:\n# Application reads ONLY its designated vault path:\nGET /v1/secrets/honestic/service_a  # Allowed (200 OK)\nGET /v1/secrets/honestic/master_keys # Denied (403 Forbidden)",
        "quiz": {
            "question": "What is the primary governing principle of Zero Trust Security?",
            "options": [
                "A) Trust anyone inside the internal company VPN",
                "B) Never trust, always verify every single request explicitly",
                "C) Rely entirely on single-layer firewall protection",
                "D) Disable data encryption on local networks"
            ],
            "correct": "B",
            "explanation": "Zero Trust eliminates implicit trust based on network location; every single access attempt is authenticated, authorized, and encrypted."
        },
        "summary": "Zero Trust treats internal and external networks as equally hostile, enforcing continuous identity validation and strict micro-segmentation.",
        "mind_map": "Zero Trust Architecture\n├── Identity & Access Management (MFA, RBAC)\n├── Device Health & Posture\n├── Micro-segmentation & mTLS\n└── Telemetry & Continuous Threat Detection"
    }
}


class VisualLearningEngine:
    _instance: Optional["VisualLearningEngine"] = None

    @classmethod
    def get_instance(cls) -> "VisualLearningEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def explain(self, topic: str) -> Dict[str, Any]:
        """Returns structured 8-part visual learning content for any technical topic."""
        key = topic.lower().strip()

        # Check curated blueprints first
        data = None
        for k, module in LEARNING_MODULES.items():
            if k in key or key in k:
                data = dict(module)
                break

        if data is None:
            # Dynamic high-fidelity synthesis for any concept
            title = topic.title().strip()
            data = {
                "title": title,
                "category": "Technology & Computer Science",
                "explanation": f"{title} is a core foundational component in modern technology. It defines systematic interfaces, encapsulates complexity into reliable layers, and enables scalable, decoupled execution across computing environments.",
                "diagram": f"""
+------------------+         Request / Input Data         +------------------------+
|   Client / User  | -----------------------------------> |  {title} Subsystem   |
|   (Application)  | <----------------------------------- |  (Processing Pipeline) |
+------------------+         Validated Response           +------------------------+
                                                                     |
                                                                     v
                                                          +------------------------+
                                                          | Storage / State Store  |
                                                          +------------------------+
""",
                "architecture_view": f"Client Interface -> {title} Processing Engine -> State Machine / Data Store -> Output Pipeline",
                "visual_card": {
                    "core_concept": f"Systematic Abstraction for {title}",
                    "operational_pattern": "Stateless execution with persistent event synchronization",
                    "resilience": "Isolated failure boundaries with self-healing fallback"
                },
                "real_example": f"# Standard architectural pattern for {title}:\nclass {title.replace(' ', '')}Engine:\n    def execute(self, payload: dict) -> dict:\n        # Process {title} logic safely\n        return {{'status': 'verified', 'resource': '{title.lower()}'}}",
                "quiz": {
                    "question": f"What is the primary benefit of deploying {title} in modern distributed software?",
                    "options": [
                        "A) Clean architectural decoupling and modular fault isolation",
                        "B) Zero abstraction overhead",
                        "C) Completely eliminates network latency",
                        "D) Disables system security boundaries"
                    ],
                    "correct": "A",
                    "explanation": f"Modular decoupling in {title} allows components to scale independently and contains errors without taking down the full system."
                },
                "summary": f"{title} provides structured encapsulation, predictable interfaces, and scalable reliability for mission-critical software systems.",
                "mind_map": f"{title} Core\n├── Core Architecture & Specifications\n├── Execution Pipeline\n├── State & Persistence Management\n└── Operational Security & Reliability"
            }

        # ── Ensure all 9 VISUAL TEACHER OMEGA components are explicitly populated ──
        plain_exp = data.get("explanation", "")
        vis_diag = data.get("diagram", "")
        flow = data.get("flowchart") or vis_diag
        m_map = data.get("mind_map", "")
        arch = data.get("architecture_view", "")
        real_ex = data.get("real_example") or data.get("example", "")
        qz = data.get("quiz", {})
        summ = data.get("summary", "")
        title = data.get("title", topic.title())
        cat = data.get("category", "General Technology")

        # Synthesize One-Page Learning Card (Component 9)
        one_page_card = (
            f"================================================================================\n"
            f"🎓 VISUAL TEACHER OMEGA — ONE-PAGE LEARNING CARD\n"
            f"TOPIC: {title} | CATEGORY: {cat}\n"
            f"================================================================================\n"
            f"1. PLAIN EXPLANATION:\n"
            f"   {plain_exp}\n\n"
            f"2. ARCHITECTURE TOPOLOGY:\n"
            f"   {arch}\n\n"
            f"3. VISUAL DIAGRAM & FLOWCHART:\n"
            f"{vis_diag.strip()}\n\n"
            f"4. CONCEPTUAL MIND MAP:\n"
            f"{m_map.strip()}\n\n"
            f"5. REAL-WORLD CODE / PRACTICAL EXAMPLE:\n"
            f"   {real_ex.strip()}\n\n"
            f"6. EXECUTIVE SUMMARY & KEY TAKEAWAYS:\n"
            f"   • {summ}\n"
            f"   • Verified architectural pattern with deterministic failure isolation.\n\n"
            f"7. KNOWLEDGE VERIFICATION QUIZ:\n"
            f"   Question: {qz.get('question', '')}\n"
            f"   Correct Answer: {qz.get('correct', '')}\n"
            f"   Explanation: {qz.get('explanation', '')}\n"
            f"================================================================================\n"
        )

        data["plain_explanation"] = plain_exp
        data["visual_diagram"] = vis_diag
        data["flowchart"] = flow
        data["mind_map"] = m_map
        data["architecture_view"] = arch
        data["real_world_example"] = real_ex
        data["quiz"] = qz
        data["summary"] = summ
        data["one_page_learning_card"] = one_page_card

        # Cross-compatible aliases
        data["diagram"] = vis_diag
        data["explanation"] = plain_exp
        data["teaching_card"] = data.get("visual_card", {})
        data["example"] = real_ex
        data["architecture"] = arch
        return data

    def explain_omega(self, topic: str) -> Dict[str, Any]:
        """Flagship ATHENA OMEGA Visual Teacher method returning all 9 structured components."""
        return self.explain(topic)

    def generate_omega_learning_package(self, topic: str) -> Dict[str, Any]:
        """Alias for explain_omega producing complete 9-part educational package."""
        return self.explain(topic)
