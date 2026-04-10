import os
from pathlib import Path
import getpass
import yaml
import shutil
from . import config as av_config

def run_init():
    print("Welcome to Atomic Vault Init Wizard")
    print("-" * 35)
    
    # Vault Root
    default_vault = str(Path.home() / "atomic-vault")
    vault_root = input(f"Enter vault root directory [{default_vault}]: ") or default_vault
    vault_root = str(Path(vault_root).expanduser().absolute())
    v_path = Path(vault_root)
    
    # 1. Scaffold Directories
    v_path.mkdir(parents=True, exist_ok=True)
    (v_path / "Raw").mkdir(exist_ok=True)
    (v_path / "Logs").mkdir(exist_ok=True)
    (v_path / "Atomic Notes").mkdir(exist_ok=True)
    (v_path / ".av-db").mkdir(exist_ok=True)
    
    domains = ["Security", "DevOps", "AWS", "Linux", "Networking", "Programming", "AI-LLM", "Misc"]
    for domain in domains:
        (v_path / "Atomic Notes" / domain).mkdir(exist_ok=True)
        
    # 2. Deploy Variant Files (AGENT.md)
    src_agent = Path(__file__).parent.parent / "AGENT.md"
    if src_agent.exists():
        shutil.copy(src_agent, v_path / "AGENT.md")
        
    # 3. Initialize index.md with Domain Headers
    index_path = v_path / "index.md"
    if not index_path.exists():
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("# Index\n\n")
            for domain in domains:
                f.write(f"## {domain}\n\n")
            f.write("## Recent Updates\n\n")

    # 4. schema.md is deprecated - replaced by AGENT.md

    # 5. Provider Selection
    providers = list(av_config.PROVIDERS.keys())
    print("\nSelect LLM Provider:")
    for i, p in enumerate(providers, 1):
        print(f"{i}. {p}")
        
    p_idx = int(input("Enter selection [1]: ") or 1) - 1
    provider = providers[p_idx]
    
    # 6. Model Selection
    models = av_config.PROVIDERS[provider]["models"]
    print(f"\nSelect {provider} Model [1]:")
    for i, m in enumerate(models, 1):
        print(f"{i}. {m}")
        
    m_idx = int(input("Enter selection: ") or 1) - 1
    model = models[m_idx]
    
    # 7. API Key
    api_key = ""
    if provider == "github_copilot":
        print("\nGitHub Copilot selected. Token will be required.")
    elif provider != "ollama":
        api_key = getpass.getpass(f"Enter {provider} API Key: ")
        
    # 8. Save Config
    conf = {
        "vault_root": vault_root,
        "provider": provider,
        "model": model,
        "api_key": api_key
    }
    
    config_dir = Path.home() / ".config" / "atomic-vault"
    config_dir.mkdir(parents=True, exist_ok=True)
    with open(config_dir / "config.yaml", "w") as f:
        yaml.dump(conf, f)
            
    print(f"\n✓ Vault initialized at {vault_root}")
    print("✓ AGENT.md variant deployed to vault root.")
    print("✓ Config saved to ~/.config/atomic-vault/config.yaml")
