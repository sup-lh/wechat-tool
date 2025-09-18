#!/usr/bin/env python3
"""
微信公众号工具主程序
支持公众号绑定验证和草稿箱发布功能
"""
import click
from colorama import init, Fore, Style
from config import ConfigManager
from wechat_api import WeChatAPI

# 初始化colorama用于彩色输出
init()

def print_success(message):
    """打印成功消息"""
    print(f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}")

def print_error(message):
    """打印错误消息"""
    print(f"{Fore.RED}❌ {message}{Style.RESET_ALL}")

def print_info(message):
    """打印信息消息"""
    print(f"{Fore.BLUE}ℹ️  {message}{Style.RESET_ALL}")

def print_warning(message):
    """打印警告消息"""
    print(f"{Fore.YELLOW}⚠️  {message}{Style.RESET_ALL}")

@click.group()
def cli():
    """微信公众号工具 - 支持绑定验证和草稿箱发布"""
    print_info("微信公众号工具 v1.0")
    print_info("支持公众号绑定验证和草稿箱发布功能")

@cli.command()
@click.option('--name', '-n', required=True, help='配置名称')
@click.option('--appid', '-a', required=True, help='公众号AppID')
@click.option('--secret', '-s', required=True, help='公众号AppSecret')
@click.option('--token', '-t', help='消息服务器Token（可选）')
def bind(name, appid, secret, token):
    """绑定微信公众号配置"""
    print_info(f"开始验证公众号配置: {name}")

    # 初始化API和配置管理器
    wechat_api = WeChatAPI()
    config_manager = ConfigManager()

    # 验证配置是否正确
    print_info("正在验证AppID和AppSecret...")
    if wechat_api.validate_wechat_config(appid, secret):
        print_success("公众号配置验证成功!")

        # 保存配置
        if config_manager.save_wx_config(name, appid, secret, token):
            print_success(f"配置已保存: {name}")
            print_info(f"AppID: {appid}")
            print_info("AppSecret: " + "*" * (len(secret) - 8) + secret[-8:])
            if token:
                print_info(f"Token: {token}")
        else:
            print_error("保存配置失败")
    else:
        print_error("公众号配置验证失败，请检查AppID和AppSecret是否正确")

@cli.command()
@click.option('--name', '-n', required=True, help='使用的配置名称')
@click.option('--title', '-t', default='测试文章', help='文章标题')
@click.option('--content', '-c', default='这是一篇通过Python工具发布的测试文章', help='文章内容')
def publish(name, title, content):
    """发布文章到草稿箱"""
    print_info(f"开始发布文章到草稿箱，使用配置: {name}")

    # 初始化配置管理器和API
    config_manager = ConfigManager()
    wechat_api = WeChatAPI()

    # 获取配置
    config = config_manager.get_wx_config(name)
    if not config:
        print_error(f"未找到配置: {name}")
        print_warning("请先使用 'bind' 命令绑定公众号配置")
        return

    appid = config['appid']
    secret = config['secret']

    print_info(f"使用公众号: {appid}")
    print_info(f"文章标题: {title}")

    # 执行发布流程
    success = wechat_api.publish_to_draft(appid, secret, title, content)

    if success:
        print_success("文章已成功发布到草稿箱!")
    else:
        print_error("发布失败，请检查配置和网络连接")

@cli.command()
def list():
    """列出所有已绑定的配置"""
    config_manager = ConfigManager()
    configs = config_manager.list_configs()

    if not configs:
        print_warning("暂无已绑定的配置")
        print_info("使用 'bind' 命令添加公众号配置")
        return

    print_info("已绑定的公众号配置:")
    for name, config in configs.items():
        print(f"  📱 {Fore.CYAN}{name}{Style.RESET_ALL}")
        print(f"     AppID: {config['appid']}")
        print(f"     Secret: {'*' * (len(config['secret']) - 8)}{config['secret'][-8:]}")

@cli.command()
@click.option('--name', '-n', required=True, help='要删除的配置名称')
@click.confirmation_option(prompt='确定要删除这个配置吗?')
def delete(name):
    """删除指定的配置"""
    config_manager = ConfigManager()

    if config_manager.delete_config(name):
        print_success(f"配置 '{name}' 已删除")
    else:
        print_error(f"配置 '{name}' 不存在")

@cli.command()
@click.option('--name', '-n', required=True, help='要测试的配置名称')
def test(name):
    """测试指定配置的连接"""
    config_manager = ConfigManager()
    wechat_api = WeChatAPI()

    config = config_manager.get_wx_config(name)
    if not config:
        print_error(f"未找到配置: {name}")
        return

    print_info(f"测试配置连接: {name}")

    if wechat_api.validate_wechat_config(config['appid'], config['secret']):
        print_success("连接测试成功!")
    else:
        print_error("连接测试失败，请检查配置")

@cli.command()
@click.option('--name', '-n', required=True, help='使用的配置名称')
@click.option('--port', '-p', default=443, help='服务器端口（默认443用于HTTPS）')
@click.option('--host', '-h', default='0.0.0.0', help='服务器地址')
@click.option('--domain', '-d', default='your-domain.com', help='外网访问域名')
def server(name, port, host, domain):
    """启动消息监听服务器"""
    print_info(f"准备启动消息监听服务器，使用配置: {name}")

    config_manager = ConfigManager()
    config = config_manager.get_wx_config(name)

    if not config:
        print_error(f"未找到配置: {name}")
        print_warning("请先使用 'bind' 命令绑定公众号配置")
        return

    token = config.get('token')
    if not token:
        print_error("该配置缺少Token，请重新绑定并提供Token")
        print_warning("使用命令: python main.py bind -n <name> -a <appid> -s <secret> -t <token>")
        return

    print_info(f"使用公众号: {config['appid']}")
    print_info(f"Token: {token}")
    print_info(f"本地服务器: http://{host}:{port}")

    # 根据端口判断协议
    protocol = "https" if port == 443 else "http"
    callback_url = f"{protocol}://{domain}/wechat"
    print_info(f"微信回调URL: {callback_url}")

    if port == 443:
        print_warning("HTTPS模式需要SSL证书，建议使用nginx反向代理")
        print_info("或者使用其他端口进行测试: -p 8080")

    print_success("启动消息监听服务器...")

    # 动态修改message_server中的token
    import message_server
    message_server.message_server.token = token

    try:
        message_server.app.run(host=host, port=port, debug=False)
    except KeyboardInterrupt:
        print_warning("服务器已停止")
    except Exception as e:
        print_error(f"服务器启动失败: {e}")

if __name__ == '__main__':
    try:
        cli()
    except KeyboardInterrupt:
        print_warning("\n操作已取消")
    except Exception as e:
        print_error(f"发生错误: {e}")