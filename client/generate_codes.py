#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
乐谱二维码生成器 - VPS版本
功能：批量生成唯一的二维码、制作PDF文件、同步到VPS服务器
"""

import os
import json
import uuid
import qrcode
import requests
import hashlib
import hmac
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from typing import List, Dict, Tuple, Optional
import secrets
import string
import subprocess
import sys
import re
import time

# 导入配置
from config import ClientConfig

class VPSQRCodeGenerator:
    """VPS版本二维码生成器类"""
    
    def __init__(self, vps_url: str = None, api_key: str = None):
        """
        初始化二维码生成器
        
        Args:
            vps_url: VPS服务器地址
            api_key: API密钥
        """
        self.config = ClientConfig()
        self.vps_url = vps_url or self.config.VPS_URL
        self.api_key = api_key or self.config.API_KEY
        
        # 本地目录配置
        self.output_dir = "output"
        self.qrcode_dir = os.path.join(self.output_dir, "qrcodes")
        self.data_dir = "data"
        
        # 创建必要的目录
        os.makedirs(self.qrcode_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        
        print(f"✅ VPS地址: {self.vps_url}")
        print(f"✅ 本地输出目录: {self.output_dir}")
    
    def generate_unique_code(self, length: int = 12) -> str:
        """
        生成唯一的验证码
        
        Args:
            length: 验证码长度
            
        Returns:
            str: 唯一验证码
        """
        # 使用字母和数字，排除容易混淆的字符
        alphabet = string.ascii_uppercase + string.digits
        alphabet = alphabet.replace('0', '').replace('O', '').replace('I', '').replace('1', '')
        
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def create_qrcode(self, code: str) -> str:
        """
        创建单个二维码
        
        Args:
            code: 验证码
            
        Returns:
            str: 二维码图片文件路径
        """
        # 构建验证URL - 指向VPS验证页面
        verify_url = f"{self.vps_url}/?code={code}"
        
        # 生成二维码
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(verify_url)
        qr.make(fit=True)
        
        # 生成二维码图片
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # 保存图片
        img_path = os.path.join(self.qrcode_dir, f"qr_{code}.png")
        qr_img.save(img_path)
        
        return img_path
    
    def generate_codes_data(self, count: int) -> List[Dict]:
        """
        生成指定数量的验证码数据
        
        Args:
            count: 生成数量
            
        Returns:
            List[Dict]: 验证码数据列表
        """
        codes_data = []
        existing_codes = set()
        
        # 读取现有验证码以避免重复
        codes_file = os.path.join(self.data_dir, "codes.json")
        if os.path.exists(codes_file):
            try:
                with open(codes_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    existing_codes = {item['code'] for item in existing_data if isinstance(item, dict) and 'code' in item}
            except:
                pass
        
        print(f"📊 已有 {len(existing_codes)} 个验证码，开始生成新的...")
        
        for i in range(count):
            # 确保验证码唯一
            while True:
                code = self.generate_unique_code()
                if code not in existing_codes:
                    existing_codes.add(code)
                    break
            
            # 创建二维码图片
            img_path = self.create_qrcode(code)
            
            code_data = {
                "code": code,
                "created_date": datetime.now().isoformat(),
                "activated": False,
                "activation_date": None,
                "img_path": img_path,
                "synced_to_vps": False,  # 新增：是否已同步到VPS
                "sync_date": None        # 新增：同步时间
            }
            
            codes_data.append(code_data)
            print(f"✅ 已生成验证码 {i+1}/{count}: {code}")
        
        return codes_data
    
    def save_codes_data(self, codes_data: List[Dict]):
        """
        保存验证码数据到JSON文件
        
        Args:
            codes_data: 验证码数据列表
        """
        # 读取现有数据
        codes_file = os.path.join(self.data_dir, "codes.json")
        existing_codes = []
        
        if os.path.exists(codes_file):
            try:
                with open(codes_file, 'r', encoding='utf-8') as f:
                    existing_codes = json.load(f)
            except:
                existing_codes = []
        
        # 合并数据
        all_codes = existing_codes + codes_data
        
        # 保存数据
        with open(codes_file, 'w', encoding='utf-8') as f:
            json.dump(all_codes, f, ensure_ascii=False, indent=2)
        
        print(f"💾 验证码数据已保存到: {codes_file}")
    
    def sync_codes_to_vps(self, codes_data: List[Dict] = None) -> Tuple[bool, str]:
        """
        同步授权码到VPS服务器
        
        Args:
            codes_data: 要同步的验证码数据，如果为None则同步所有未同步的
            
        Returns:
            Tuple[bool, str]: (成功状态, 消息)
        """
        if not self.vps_url or not self.api_key:
            return False, "❌ VPS地址或API密钥未配置"
        
        # 如果没有指定数据，读取所有未同步的数据
        if codes_data is None:
            codes_file = os.path.join(self.data_dir, "codes.json")
            if not os.path.exists(codes_file):
                return False, "❌ 没有找到验证码数据文件"
            
            try:
                with open(codes_file, 'r', encoding='utf-8') as f:
                    all_codes = json.load(f)
                
                # 筛选未同步的验证码
                codes_data = [code for code in all_codes if not code.get('synced_to_vps', False)]
                
                if not codes_data:
                    return True, "✅ 所有验证码都已同步到VPS"
                    
            except Exception as e:
                return False, f"❌ 读取验证码数据失败: {e}"
        
        # 准备同步数据
        sync_data = {
            "codes": [
                {
                    "code": code_info["code"],
                    "created_date": code_info["created_date"]
                }
                for code_info in codes_data
            ],
            "api_key": self.api_key
        }
        
        print(f"🚀 开始同步 {len(sync_data['codes'])} 个验证码到VPS...")
        
        try:
            # 发送同步请求
            response = requests.post(
                f"{self.vps_url}/api/sync-codes",
                json=sync_data,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # 更新本地数据，标记为已同步
                self._mark_codes_as_synced([code["code"] for code in sync_data["codes"]])
                
                stats = result.get('stats', {})
                message = f"✅ 同步成功！添加: {stats.get('added', 0)}, 跳过: {stats.get('skipped', 0)}, 错误: {stats.get('errors', 0)}"
                
                return True, message
            else:
                error_info = response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
                return False, f"❌ 同步失败 ({response.status_code}): {error_info}"
                
        except requests.exceptions.ConnectionError:
            return False, f"❌ 无法连接到VPS服务器: {self.vps_url}"
        except requests.exceptions.Timeout:
            return False, "❌ 请求超时，请检查网络连接"
        except Exception as e:
            return False, f"❌ 同步过程中发生错误: {e}"
    
    def _mark_codes_as_synced(self, synced_codes: List[str]):
        """
        标记验证码为已同步
        
        Args:
            synced_codes: 已同步的验证码列表
        """
        codes_file = os.path.join(self.data_dir, "codes.json")
        if not os.path.exists(codes_file):
            return
        
        try:
            with open(codes_file, 'r', encoding='utf-8') as f:
                all_codes = json.load(f)
            
            # 更新同步状态
            sync_time = datetime.now().isoformat()
            for code_info in all_codes:
                if code_info["code"] in synced_codes:
                    code_info["synced_to_vps"] = True
                    code_info["sync_date"] = sync_time
            
            # 保存更新后的数据
            with open(codes_file, 'w', encoding='utf-8') as f:
                json.dump(all_codes, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"⚠️ 更新同步状态失败: {e}")
    
    def check_vps_status(self) -> Tuple[bool, Dict]:
        """
        检查VPS服务器状态
        
        Returns:
            Tuple[bool, Dict]: (连接状态, 服务器信息)
        """
        if not self.vps_url:
            return False, {"error": "VPS地址未配置"}
        
        try:
            response = requests.get(f"{self.vps_url}/api/status", timeout=10)
            
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, {"error": f"服务器返回错误: {response.status_code}"}
                
        except requests.exceptions.ConnectionError:
            return False, {"error": f"无法连接到服务器: {self.vps_url}"}
        except requests.exceptions.Timeout:
            return False, {"error": "连接超时"}
        except Exception as e:
            return False, {"error": f"检查状态时发生错误: {e}"}
    
    def create_pdf(self, codes_data: List[Dict], orientation: str = "landscape"):
        """
        创建可打印的PDF文件（保持原有功能）
        
        Args:
            codes_data: 验证码数据列表
            orientation: 页面方向，"landscape"(横版) 或 "portrait"(竖版)
        """
        if orientation == "landscape":
            self._create_landscape_pdf(codes_data)
        elif orientation == "portrait":
            self._create_portrait_pdf(codes_data)
        else:
            raise ValueError("orientation must be 'landscape' or 'portrait'")
    
    def _create_landscape_pdf(self, codes_data: List[Dict]):
        """创建横版A4 PDF文件"""
        pdf_path = os.path.join(self.output_dir, "qrcode_sheet_横版.pdf")
        
        # 创建横版A4 PDF文档
        from reportlab.lib.pagesizes import landscape, A4
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=landscape(A4),
            rightMargin=3*cm,
            leftMargin=3*cm,
            topMargin=3*cm,
            bottomMargin=3*cm
        )
        
        # 注册字体
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        # 尝试注册字体
        try:
            pdfmetrics.registerFont(TTFont('Bodoni72', 'fonts/Bodoni 72.ttc'))
            title_font = 'Bodoni72'
        except:
            try:
                pdfmetrics.registerFont(TTFont('BrushScript', '/System/Library/Fonts/Supplemental/Brush Script.ttf'))
                title_font = 'BrushScript'
            except:
                try:
                    pdfmetrics.registerFont(TTFont('Baskerville', '/System/Library/Fonts/Baskerville.ttc'))
                    title_font = 'Baskerville'
                except:
                    title_font = 'Times-Roman'
        
        try:
            pdfmetrics.registerFont(TTFont('PTSerif', '/System/Library/Fonts/Supplemental/PTSerif.ttc'))
            code_font = 'PTSerif'
        except:
            try:
                pdfmetrics.registerFont(TTFont('Monaco', '/System/Library/Fonts/Monaco.ttf'))
                code_font = 'Monaco'
            except:
                code_font = 'Courier-Bold'
        
        # 样式
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Normal'],
            fontName=title_font,
            fontSize=24,
            spaceAfter=40,
            alignment=TA_CENTER,
            textColor=colors.black
        )
        
        code_style = ParagraphStyle(
            'CodeStyle',
            parent=styles['Normal'],
            fontName=code_font,
            fontSize=18,
            spaceBefore=20,
            alignment=TA_CENTER,
            textColor=colors.black
        )
        
        story = []
        
        # 为每个验证码创建一页
        for i, code_data in enumerate(codes_data):
            if i > 0:
                from reportlab.platypus import PageBreak
                story.append(PageBreak())
            
            story.append(Spacer(1, 2*cm))
            
            # 标题文字
            title_text = "SCAN TO VERIFY AUTHENTICITY."
            title = Paragraph(title_text, title_style)
            story.append(title)
            
            # 二维码图片
            img_path = code_data['img_path']
            if os.path.exists(img_path):
                from reportlab.platypus import Image
                qr_img = Image(img_path, width=6*cm, height=6*cm)
                qr_img.hAlign = 'CENTER'
                story.append(qr_img)
            
            # 验证码文本
            code_text = Paragraph(code_data['code'], code_style)
            story.append(code_text)
        
        # 生成PDF
        doc.build(story)
        print(f"📄 横版PDF文件已生成: {pdf_path}")
        print(f"🎨 标题字体：{title_font}，验证码字体：{code_font}")
        print(f"📝 包含 {len(codes_data)} 页")

    def _create_portrait_pdf(self, codes_data: List[Dict]):
        """创建竖版A4 PDF文件"""
        pdf_path = os.path.join(self.output_dir, "qrcode_sheet_竖版.pdf")
        
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=2.5*cm,
            leftMargin=2.5*cm,
            topMargin=2.5*cm,
            bottomMargin=2.5*cm
        )
        
        # 字体配置（与横版相同）
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        try:
            pdfmetrics.registerFont(TTFont('Bodoni72', 'fonts/Bodoni 72.ttc'))
            title_font = 'Bodoni72'
        except:
            title_font = 'Times-Roman'
        
        try:
            pdfmetrics.registerFont(TTFont('PTSerif', '/System/Library/Fonts/Supplemental/PTSerif.ttc'))
            code_font = 'PTSerif'
        except:
            code_font = 'Courier-Bold'
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'PortraitTitle',
            parent=styles['Normal'],
            fontName=title_font,
            fontSize=20,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.black,
            leading=24
        )
        
        code_style = ParagraphStyle(
            'PortraitCode',
            parent=styles['Normal'],
            fontName=code_font,
            fontSize=16,
            spaceBefore=15,
            alignment=TA_CENTER,
            textColor=colors.black,
            leading=20
        )
        
        story = []
        
        for i, code_data in enumerate(codes_data):
            if i > 0:
                from reportlab.platypus import PageBreak
                story.append(PageBreak())
            
            story.append(Spacer(1, 4*cm))
            
            title_text = "SCAN TO VERIFY AUTHENTICITY."
            title = Paragraph(title_text, title_style)
            story.append(title)
            
            story.append(Spacer(1, 1.5*cm))
            
            img_path = code_data['img_path']
            if os.path.exists(img_path):
                from reportlab.platypus import Image
                qr_size = 7*cm
                qr_img = Image(img_path, width=qr_size, height=qr_size)
                qr_img.hAlign = 'CENTER'
                story.append(qr_img)
            
            story.append(Spacer(1, 1*cm))
            
            code_text = Paragraph(code_data['code'], code_style)
            story.append(code_text)
            
            story.append(Spacer(1, 1*cm))
        
        doc.build(story)
        print(f"📄 竖版PDF文件已生成: {pdf_path}")
        print(f"🎨 标题字体：{title_font}，验证码字体：{code_font}")
        print(f"📝 包含 {len(codes_data)} 页")
    
    def generate_batch(self, count: int = 50, orientation: str = "landscape", auto_sync: bool = True):
        """
        批量生成二维码并同步到VPS
        
        Args:
            count: 生成数量，默认50个
            orientation: PDF页面方向，"landscape"(横版) 或 "portrait"(竖版)
            auto_sync: 是否自动同步到VPS
        """
        print(f"🎯 开始生成 {count} 个验证码...")
        orientation_text = "横版" if orientation == "landscape" else "竖版"
        print(f"📄 PDF格式：{orientation_text}A4")
        
        # 检查VPS连接状态
        if auto_sync:
            print("\n🔍 检查VPS服务器状态...")
            vps_ok, vps_info = self.check_vps_status()
            if vps_ok:
                stats = vps_info.get('stats', {})
                print(f"✅ VPS连接正常")
                print(f"📊 服务器统计: 总码数 {stats.get('total_codes', 0)}, 已激活 {stats.get('activated_codes', 0)}")
            else:
                print(f"⚠️ VPS连接异常: {vps_info.get('error', '未知错误')}")
                auto_sync = False
        
        # 生成验证码数据
        codes_data = self.generate_codes_data(count)
        
        # 保存数据
        self.save_codes_data(codes_data)
        
        # 创建PDF
        self.create_pdf(codes_data, orientation)
        
        # 同步到VPS
        if auto_sync:
            print("\n🚀 正在同步到VPS服务器...")
            sync_ok, sync_msg = self.sync_codes_to_vps(codes_data)
            print(sync_msg)
        
        print(f"\n✅ 批量生成完成！")
        print(f"📁 二维码图片目录: {self.qrcode_dir}")
        pdf_filename = f"qrcode_sheet_{orientation_text}.pdf"
        print(f"📄 PDF文件: {os.path.join(self.output_dir, pdf_filename)}")
        print(f"💾 数据文件: {os.path.join(self.data_dir, 'codes.json')}")
        if auto_sync and sync_ok:
            print(f"🌐 已同步到VPS: {self.vps_url}")
        
        return codes_data


def main():
    """主函数"""
    print("=== 乐谱二维码生成器 - VPS版本 ===")
    print("✅ 支持自动同步到VPS服务器")
    print()

    # 获取用户输入
    try:
        count = int(input("请输入要生成的二维码数量 (默认50): ") or "50")
        if count <= 0:
            print("❌ 数量必须大于0")
            return
    except ValueError:
        print("❌ 请输入有效的数字")
        return

    # 选择PDF格式
    print("\n请选择PDF页面格式:")
    print("1. 横版A4 (29.7×21cm) - 适合横向布局，传统格式")
    print("2. 竖版A4 (21×29.7cm) - 遵循黄金比例，优雅设计")
    format_choice = input("请输入选择 (1或2，默认1): ").strip() or "1"

    if format_choice == "1":
        orientation = "landscape"
        print("✅ 选择横版A4格式")
    elif format_choice == "2":
        orientation = "portrait"
        print("✅ 选择竖版A4格式（黄金比例设计）")
    else:
        print("❌ 无效选择，使用默认横版格式")
        orientation = "landscape"

    # 是否自动同步到VPS
    sync_choice = input("\n是否自动同步到VPS服务器？(Y/n): ").strip().lower()
    auto_sync = sync_choice != 'n'

    # 创建生成器实例
    generator = VPSQRCodeGenerator()

    # 批量生成
    generator.generate_batch(count, orientation, auto_sync)

    print("\n🎉 生成完成！")
    print("📋 接下来的步骤：")
    if auto_sync:
        print("1. 验证码已自动同步到VPS服务器")
    else:
        print("1. 如需同步到VPS，请稍后运行同步功能")
    if orientation == "portrait":
        print("2. 使用生成的竖版PDF进行书籍印刷（黄金比例设计，更优雅）")
    else:
        print("2. 使用生成的横版PDF进行书籍印刷")
    print("3. 用户扫描二维码即可验证真伪")
    print(f"4. 二维码指向: {generator.vps_url}")


if __name__ == "__main__":
    main()
