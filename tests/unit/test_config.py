"""
配置系统单元测试

测试配置模式验证、加载器功能、兼容性修复等核心功能。
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from ruamel.yaml import YAML

from inspa.config.loader import ConfigLoader, ConfigValidationError, ConfigError, load_config, validate_config
from inspa.config.schema import (
    CompressionAlgorithm,
    CompressionModel,
    EnvironmentModel,
    InputPathModel,
    InspaConfig,
    InstallModel,
    PostActionModel,
    ProductModel,
    ResourcesModel,
    RunCondition,
    ScriptType,
    UIModel,
)


class TestProductModel:
    """ProductModel 测试"""

    def test_valid_product_model(self):
        """测试有效的产品模型"""
        product = ProductModel(
            name="TestApp",
            version="1.0.0",
            company="Test Company",
            description="Test Description",
            copyright="© 2024 Test Company",
            website="https://example.com"
        )
        assert product.name == "TestApp"
        assert product.version == "1.0.0"

    def test_version_validation(self):
        """测试版本号验证"""
        # 有效的版本号格式
        valid_versions = ["1.0.0", "1.2.3-beta.1", "1.0", "25.9.25", "2024.01.01"]
        for version in valid_versions:
            product = ProductModel(name="Test", version=version)
            assert product.version == version

        # 无效的版本号格式
        invalid_versions = ["invalid", "1.0.0.0.0", "v1.0.0"]
        for version in invalid_versions:
            with pytest.raises(ValidationError):
                ProductModel(name="Test", version=version)

    def test_product_model_defaults(self):
        """测试产品模型默认值"""
        product = ProductModel(name="TestApp", version="1.0.0")
        assert product.company is None
        assert product.description is None
        assert product.copyright is None
        assert product.website is None


class TestInstallModel:
    """InstallModel 测试"""

    def test_valid_install_model(self):
        """测试有效的安装模型"""
        install = InstallModel(
            default_path="C:/Program Files/TestApp",
            allow_user_path=True,
            force_hidden_path=False,
            silent_allowed=True,
            require_admin=False
        )
        assert install.default_path == "C:/Program Files/TestApp"

    def test_path_validation(self):
        """测试路径验证"""
        # 有效的路径
        InstallModel(default_path="C:/Program Files/TestApp", allow_user_path=True)

        # 空路径应该失败
        with pytest.raises(ValidationError):
            InstallModel(default_path="", allow_user_path=True)

    def test_path_settings_validation(self):
        """测试路径设置一致性验证"""
        # force_hidden_path 和 allow_user_path 不能同时为 true
        with pytest.raises(ValidationError):
            InstallModel(
                default_path="C:/Test",
                allow_user_path=True,
                force_hidden_path=True
            )

    def test_file_validation(self):
        """测试文件路径验证"""
        # 有效的文件类型
        install = InstallModel(
            default_path="C:/Test",
            license_file="license.txt",
            privacy_file="privacy.md"
        )
        assert install.license_file.name == "license.txt"

        # 无效的文件类型
        with pytest.raises(ValidationError):
            InstallModel(
                default_path="C:/Test",
                license_file="license.exe"
            )


class TestCompressionModel:
    """CompressionModel 测试"""

    def test_valid_compression_model(self):
        """测试有效的压缩模型"""
        compression = CompressionModel(
            algo=CompressionAlgorithm.ZSTD,
            level=10,
            fallback_to_zip=True
        )
        assert compression.algo == CompressionAlgorithm.ZSTD
        assert compression.level == 10

    def test_compression_level_validation(self):
        """测试压缩级别验证"""
        # Zstd 有效级别
        CompressionModel(algo=CompressionAlgorithm.ZSTD, level=1)
        CompressionModel(algo=CompressionAlgorithm.ZSTD, level=22)

        # Zstd 无效级别
        with pytest.raises(ValidationError):
            CompressionModel(algo=CompressionAlgorithm.ZSTD, level=0)
        with pytest.raises(ValidationError):
            CompressionModel(algo=CompressionAlgorithm.ZSTD, level=23)

        # Zip 有效级别
        CompressionModel(algo=CompressionAlgorithm.ZIP, level=1)
        CompressionModel(algo=CompressionAlgorithm.ZIP, level=9)

        # Zip 无效级别
        with pytest.raises(ValidationError):
            CompressionModel(algo=CompressionAlgorithm.ZIP, level=0)
        with pytest.raises(ValidationError):
            CompressionModel(algo=CompressionAlgorithm.ZIP, level=10)


class TestInputPathModel:
    """InputPathModel 测试"""

    def test_valid_input_path_model(self):
        """测试有效的输入路径模型"""
        input_path = InputPathModel(
            path="C:/source",
            recursive=True,
            preserve_structure=True
        )
        assert input_path.path == Path("C:/source")
        assert input_path.recursive is True
        assert input_path.preserve_structure is True

    def test_path_conversion(self):
        """测试路径转换"""
        input_path = InputPathModel(path="C:/source")
        assert isinstance(input_path.path, Path)
        assert str(input_path.path) == "C:\\source"


class TestPostActionModel:
    """PostActionModel 测试"""

    def test_valid_post_action_model(self):
        """测试有效的后置动作模型"""
        action = PostActionModel(
            type=ScriptType.POWERSHELL,
            command="setup.ps1",
            args=["-param1", "value1"],
            hidden=True,
            timeout_sec=300,
            show_in_ui=True,
            run_if=RunCondition.SUCCESS,
            working_dir="scripts"
        )
        assert action.type == ScriptType.POWERSHELL
        assert action.command == "setup.ps1"
        assert action.timeout_sec == 300

    def test_command_validation(self):
        """测试命令验证"""
        # 有效的命令
        PostActionModel(type=ScriptType.BATCH, command="setup.bat")

        # 空命令应该失败
        with pytest.raises(ValidationError):
            PostActionModel(type=ScriptType.BATCH, command="")


class TestEnvironmentModel:
    """EnvironmentModel 测试"""

    def test_valid_environment_model(self):
        """测试有效的环境模型"""
        env = EnvironmentModel(
            add_path=["C:/bin", "C:/tools"],
            set={"MY_VAR": "value"},
            system_scope=False
        )
        assert env.add_path == ["C:/bin", "C:/tools"]
        assert env.set == {"MY_VAR": "value"}

    def test_add_path_processing(self):
        """测试 PATH 添加处理"""
        # 去除空白和重复项
        env = EnvironmentModel(add_path=["C:/bin", "  ", "C:/bin", "C:/tools"])
        assert env.add_path == ["C:/bin", "C:/tools"]

        # 空列表处理
        env = EnvironmentModel(add_path=["", "  "])
        assert env.add_path is None


class TestInspaConfig:
    """InspaConfig 测试"""

    def test_minimal_valid_config(self):
        """测试最小有效配置"""
        config = InspaConfig(
            product=ProductModel(name="TestApp", version="1.0.0"),
            install=InstallModel(default_path="C:/TestApp"),
            inputs=[InputPathModel(path="C:/source")]
        )
        assert config.product.name == "TestApp"
        assert len(config.inputs) == 1

    def test_config_with_all_options(self):
        """测试包含所有选项的配置"""
        config = InspaConfig(
            product=ProductModel(
                name="TestApp",
                version="1.0.0",
                company="Test Company",
                description="Test Description"
            ),
            install=InstallModel(
                default_path="C:/Program Files/TestApp",
                allow_user_path=True,
                require_admin=True
            ),
            inputs=[InputPathModel(path="C:/source")],
            resources=ResourcesModel(icon="icon.ico"),
            ui=UIModel(theme="github-light"),
            compression=CompressionModel(algo=CompressionAlgorithm.ZSTD, level=10),
            exclude=["*.tmp", "*.log"],
            post_actions=[
                PostActionModel(
                    type=ScriptType.POWERSHELL,
                    command="setup.ps1"
                )
            ],
            env=EnvironmentModel(add_path=["C:/bin"])
        )
        assert config.install.icon_path == Path("icon.ico")
        assert config.compression.algo == CompressionAlgorithm.ZSTD
        assert len(config.post_actions) == 1

    def test_admin_requirements_validation(self):
        """测试管理员权限需求验证"""
        # Program Files 路径应该自动设置 require_admin
        config = InspaConfig(
            product=ProductModel(name="TestApp", version="1.0.0"),
            install=InstallModel(default_path="%ProgramFiles%/TestApp"),
            inputs=[InputPathModel(path="C:/source")]
        )
        assert config.install.require_admin is True

    def test_config_to_dict(self):
        """测试配置转字典"""
        config = InspaConfig(
            product=ProductModel(name="TestApp", version="1.0.0"),
            install=InstallModel(default_path="C:/TestApp"),
            inputs=[InputPathModel(path="C:/source")]
        )
        data = config.to_dict()
        assert data["product"]["name"] == "TestApp"
        assert "config" in data  # 应该包含配置元信息

    def test_config_from_dict(self):
        """测试从字典创建配置"""
        data = {
            "product": {
                "name": "TestApp",
                "version": "1.0.0"
            },
            "install": {
                "default_path": "C:/TestApp"
            },
            "inputs": [
                {"path": "C:/source"}
            ]
        }
        config = InspaConfig.from_dict(data)
        assert config.product.name == "TestApp"

    def test_get_version_info(self):
        """测试获取版本信息"""
        config = InspaConfig(
            product=ProductModel(
                name="TestApp",
                version="1.0.0",
                company="Test Company",
                description="Test Description",
                copyright="© 2024 Test Company"
            ),
            install=InstallModel(default_path="C:/TestApp"),
            inputs=[InputPathModel(path="C:/source")]
        )
        version_info = config.get_version_info()
        assert version_info["FileVersion"] == "1.0.0"
        assert version_info["ProductName"] == "TestApp"

    def test_get_window_title(self):
        """测试获取窗口标题"""
        # 使用自定义标题
        config = InspaConfig(
            product=ProductModel(name="TestApp", version="1.0.0"),
            install=InstallModel(default_path="C:/TestApp"),
            inputs=[InputPathModel(path="C:/source")],
            ui=UIModel(window_title="Custom Title")
        )
        assert config.get_window_title() == "Custom Title"

        # 使用默认标题
        config = InspaConfig(
            product=ProductModel(name="TestApp", version="1.0.0"),
            install=InstallModel(default_path="C:/TestApp"),
            inputs=[InputPathModel(path="C:/source")]
        )
        assert config.get_window_title() == "TestApp 安装程序"


class TestConfigLoader:
    """ConfigLoader 测试"""

    def test_init(self):
        """测试初始化"""
        loader = ConfigLoader()
        assert loader.yaml is not None

    def test_load_from_file_valid_yaml(self):
        """测试从有效 YAML 文件加载配置"""
        config_data = {
            "product": {
                "name": "TestApp",
                "version": "1.0.0"
            },
            "install": {
                "default_path": "C:/TestApp"
            },
            "inputs": [
                {"path": "C:/source"}
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml = YAML()
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            loader = ConfigLoader()
            config = loader.load_from_file(config_path)
            assert config.product.name == "TestApp"
        finally:
            config_path.unlink()

    def test_load_from_file_invalid_path(self):
        """测试从不存在的文件加载配置"""
        loader = ConfigLoader()
        with pytest.raises(ConfigError) as exc_info:
            loader.load_from_file("nonexistent.yaml")

        assert "配置文件不存在" in str(exc_info.value)

    def test_load_from_file_invalid_extension(self):
        """测试加载无效扩展名的文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("invalid")
            config_path = Path(f.name)

        try:
            loader = ConfigLoader()
            with pytest.raises(ConfigError) as exc_info:
                loader.load_from_file(config_path)

            assert "配置文件必须是 .yaml 或 .yml 格式" in str(exc_info.value)
        finally:
            config_path.unlink()

    def test_load_from_file_invalid_yaml(self):
        """测试加载无效 YAML 文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [\n")
            config_path = Path(f.name)

        try:
            loader = ConfigLoader()
            with pytest.raises(ConfigError) as exc_info:
                loader.load_from_file(config_path)

            assert "YAML 解析错误" in str(exc_info.value)
        finally:
            config_path.unlink()

    def test_load_from_dict(self):
        """测试从字典加载配置"""
        data = {
            "product": {
                "name": "TestApp",
                "version": "1.0.0"
            },
            "install": {
                "default_path": "C:/TestApp"
            },
            "inputs": [
                {"path": "C:/source"}
            ]
        }

        loader = ConfigLoader()
        config = loader.load_from_dict(data)
        assert config.product.name == "TestApp"

    def test_load_from_dict_with_base_path(self):
        """测试从字典加载配置时解析相对路径"""
        data = {
            "product": {
                "name": "TestApp",
                "version": "1.0.0"
            },
            "install": {
                "default_path": "C:/TestApp",
                "license_file": "license.txt"
            },
            "inputs": [
                {"path": "source"}
            ]
        }

        base_path = Path("C:/project")
        loader = ConfigLoader()
        config = loader.load_from_dict(data, base_path)

        # 相对路径应该被解析为绝对路径
        assert config.install.license_file == Path("C:/project/license.txt")
        assert config.inputs[0].path == Path("C:/project/source")

    def test_save_to_file(self):
        """测试保存配置到文件"""
        config = InspaConfig(
            product=ProductModel(name="TestApp", version="1.0.0"),
            install=InstallModel(default_path="C:/TestApp"),
            inputs=[InputPathModel(path="C:/source")]
        )

        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as f:
            output_path = Path(f.name)

        try:
            loader = ConfigLoader()
            loader.save_to_file(config, output_path)

            # 验证文件已创建并包含正确内容
            assert output_path.exists()
            with open(output_path, 'r', encoding='utf-8') as f:
                saved_data = loader.yaml.load(f)

            assert saved_data["product"]["name"] == "TestApp"
        finally:
            output_path.unlink()

    def test_validate_file(self):
        """测试验证配置文件"""
        config_data = {
            "product": {
                "name": "TestApp",
                "version": "1.0.0"
            },
            "install": {
                "default_path": "C:/TestApp"
            },
            "inputs": [
                {"path": "C:/source"}
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml = YAML()
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            loader = ConfigLoader()
            errors = loader.validate_file(config_path)
            assert errors == []  # 应该没有错误
        finally:
            config_path.unlink()

    def test_validate_file_with_errors(self):
        """测试验证包含错误的配置文件"""
        invalid_config_data = {
            "product": {
                "name": "",  # 无效：空名称
                "version": "invalid"  # 无效：无效版本号
            },
            "install": {
                "default_path": ""  # 无效：空路径
            },
            "inputs": []
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml = YAML()
            yaml.dump(invalid_config_data, f)
            config_path = Path(f.name)

        try:
            loader = ConfigLoader()
            errors = loader.validate_file(config_path)
            assert len(errors) > 0  # 应该有错误
        finally:
            config_path.unlink()

    def test_compatibility_fixes(self):
        """测试兼容性修复"""
        # 测试旧的 icon_path 字段迁移
        old_format_data = {
            "product": {
                "name": "TestApp",
                "version": "1.0.0"
            },
            "install": {
                "default_path": "C:/TestApp",
                "icon_path": "icon.ico"  # 直接在 install 下
            },
            "inputs": [
                {"path": "C:/source"}
            ]
        }

        loader = ConfigLoader()
        config = loader.load_from_dict(old_format_data)

        # icon_path 应该存在于 install 中
        assert config.install.icon_path == Path("icon.ico")


class TestGlobalFunctions:
    """全局函数测试"""

    def test_load_config(self):
        """测试全局 load_config 函数"""
        config_data = {
            "product": {
                "name": "TestApp",
                "version": "1.0.0"
            },
            "install": {
                "default_path": "C:/TestApp"
            },
            "inputs": [
                {"path": "C:/source"}
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml = YAML()
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            config = load_config(config_path)
            assert config.product.name == "TestApp"
        finally:
            config_path.unlink()

    def test_validate_config(self):
        """测试全局 validate_config 函数"""
        config_data = {
            "product": {
                "name": "TestApp",
                "version": "1.0.0"
            },
            "install": {
                "default_path": "C:/TestApp"
            },
            "inputs": [
                {"path": "C:/source"}
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml = YAML()
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            errors = validate_config(config_path)
            assert errors == []
        finally:
            config_path.unlink()