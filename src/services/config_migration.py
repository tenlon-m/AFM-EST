import json
import shutil
from pathlib import Path
from typing import Dict, Any, Callable, Optional
from datetime import datetime


class ConfigMigration:
    MIGRATION_STRATEGIES: Dict[str, Callable] = {}
    
    @classmethod
    def register_strategy(cls, from_version: str, to_version: str, strategy: Callable) -> None:
        key = f"{from_version}->{to_version}"
        cls.MIGRATION_STRATEGIES[key] = strategy
    
    @classmethod
    def get_migration_path(cls, from_version: str, to_version: str) -> list:
        if from_version == to_version:
            return []
        
        path = []
        current = from_version
        
        while current != to_version:
            found = False
            for key in cls.MIGRATION_STRATEGIES:
                if key.startswith(f"{current}->"):
                    _, next_version = key.split('->')
                    path.append((current, next_version))
                    current = next_version
                    found = True
                    break
            
            if not found:
                raise ValueError(f"No migration path found from {from_version} to {to_version}")
        
        return path
    
    def __init__(self, config_path: str, backup_dir: str = "config/backups"):
        self.config_path = Path(config_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def get_current_version(self) -> str:
        if not self.config_path.exists():
            return "0.0"
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config.get('version', '0.0')
        except Exception:
            return "0.0"
    
    def backup_config(self) -> Path:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version = self.get_current_version()
        backup_name = f"config_v{version}_{timestamp}.json"
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(self.config_path, backup_path)
        return backup_path
    
    def restore_backup(self, backup_path: Path) -> None:
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        shutil.copy2(backup_path, self.config_path)
    
    def migrate(self, target_version: str) -> bool:
        current_version = self.get_current_version()
        
        if current_version == target_version:
            return True
        
        try:
            backup_path = self.backup_config()
        except FileNotFoundError:
            backup_path = None
        
        try:
            migration_path = self.get_migration_path(current_version, target_version)
            
            for from_ver, to_ver in migration_path:
                strategy_key = f"{from_ver}->{to_ver}"
                strategy = self.MIGRATION_STRATEGIES.get(strategy_key)
                
                if strategy:
                    with open(self.config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    
                    migrated_config = strategy(config)
                    migrated_config['version'] = to_ver
                    
                    with open(self.config_path, 'w', encoding='utf-8') as f:
                        json.dump(migrated_config, f, ensure_ascii=False, indent=2)
            
            return True
        
        except Exception as e:
            if backup_path and backup_path.exists():
                self.restore_backup(backup_path)
            raise e


def migrate_0_9_to_1_0(config: Dict[str, Any]) -> Dict[str, Any]:
    migrated = {
        'version': '1.0',
        'ui': {
            'theme': config.get('theme', 'light'),
            'view_mode': config.get('view_mode', 'details'),
            'icon_size': config.get('icon_size', 32),
            'show_hidden_files': config.get('show_hidden', False),
            'window_size': config.get('window_size', [1200, 800]),
        },
        'search': {
            'index_path': config.get('index_path', 'index'),
            'max_threads': config.get('search_threads', 4),
        },
        'transfer': {
            'buffer_size': 8192,
            'max_retries': 3,
        },
        'quick_access': {
            'max_items': 20,
            'show_recent': True,
        },
    }
    
    return migrated


ConfigMigration.register_strategy('0.9', '1.0', migrate_0_9_to_1_0)