#!/usr/bin/env python3
  # -*- coding: utf-8 -*-
  """
  金价推送微信脚本
  数据源：新浪财经（沪金连续、COMEX黄金、沪银连续、离岸人民币）
  支持推送：Server酱、企业微信机器人、Bark(iOS)
  """

  import sys
  import io

  # 修复 Windows 终端编码问题
  sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
  sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

  import json
  import os
  import urllib.request
  import urllib.parse
  from datetime import datetime

   # ==================== 用户配置区域 ====================

  # 优先从环境变量读取密钥（适合 GitHub Actions），本地可在此硬编码
  SERVERCHAN_KEY   = os.getenv('SERVERCHAN_KEY', '')
  WECHAT_WORK_KEY  = os.getenv('WECHAT_WORK_KEY', '')
  BARK_KEY         = os.getenv('BARK_KEY', '')
  PUSHPLUS_TOKEN   = os.getenv('PUSHPLUS_TOKEN', '')

  # 调试：打印密钥是否存在（不打印值）
  print(f"   SERVERCHAN_KEY:   {'已配置' if SERVERCHAN_KEY else '未配置'}")
  print(f"   WECHAT_WORK_KEY:  {'已配置' if WECHAT_WORK_KEY else '未配置'}")
  print(f"   BARK_KEY:         {'已配置' if BARK_KEY else '未配置'}")
  print(f"   PUSHPLUS_TOKEN:   {'已配置' if PUSHPLUS_TOKEN else '未配置'}")

  # ==================== 测试模式 ====================
  # 设为 True 可使用模拟数据测试推送（无需联网）
  USE_MOCK_DATA = False

  # ==================== 金价获取 ====================

  def fetch_sina_quotes(symbols):
      """从新浪财经获取行情数据"""
      if not symbols:
          return {}

      symbol_str = ','.join(symbols)
      url = f"https://hq.sinajs.cn/list={symbol_str}"

      try:
          req = urllib.request.Request(url, headers={
              'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
              'Referer': 'https://finance.sina.com.cn'
          })
          with urllib.request.urlopen(req, timeout=15) as resp:
              text = resp.read().decode('gbk', errors='ignore')

          results = {}
          for line in text.strip().split(';'):
              line = line.strip()
              if not line:
                  continue
              # Parse: var hq_str_SYMBOL="DATA";
              match = line.split('="')
              if len(match) >= 2:
                  symbol = match[0].replace('var hq_str_', '')
                  data = match[1].rstrip('"')
                  results[symbol] = data
          return results
      except Exception as e:
          return {'_error': str(e)}


  def parse_gold_data(raw_data):
      """解析黄金行情数据"""
      data = {}

      # 国内黄金 AU0 (沪金连续)
      if 'AU0' in raw_data and raw_data['AU0']:
          parts = raw_data['AU0'].split(',')
          if len(parts) >= 20:
              data['domestic_gold'] = {
                  'name': '沪金连续',
                  'open': float(parts[2]),
                  'high': float(parts[3]),
                  'low': float(parts[4]),
                  'prev_close': float(parts[5]),
                  'bid': float(parts[6]),
                  'ask': float(parts[7]),
                  'latest': float(parts[8]),
                  'settle': float(parts[9]),
                  'prev_settle': float(parts[10]),
                  'volume': int(parts[14]),
                  'position': int(parts[13]),
                  'date': parts[17],
                  'unit': '元/克'
              }

      # 国内白银 AG0 (沪银连续)
      if 'AG0' in raw_data and raw_data['AG0']:
          parts = raw_data['AG0'].split(',')
          if len(parts) >= 20:
              data['domestic_silver'] = {
                  'name': '沪银连续',
                  'open': float(parts[2]),
                  'high': float(parts[3]),
                  'low': float(parts[4]),
                  'prev_close': float(parts[5]),
                  'bid': float(parts[6]),
                  'ask': float(parts[7]),
                  'latest': float(parts[8]),
                  'prev_settle': float(parts[10]),
                  'volume': int(parts[14]),
                  'unit': '元/千克'
              }

      # 国际黄金 hf_GC (COMEX黄金)
      if 'hf_GC' in raw_data and raw_data['hf_GC']:
          parts = raw_data['hf_GC'].split(',')
          if len(parts) >= 10:
              data['international_gold'] = {
                  'name': 'COMEX黄金',
                  'latest': float(parts[0]) if parts[0] else float(parts[2]),
                  'bid': float(parts[2]),
                  'ask': float(parts[3]),
                  'high': float(parts[4]),
                  'low': float(parts[5]),
                  'time': parts[6],
                  'prev_close': float(parts[7]),
                  'open': float(parts[8]),
                  'date': parts[12],
                  'unit': '美元/盎司'
              }

      # 国际白银 hf_SI (COMEX白银)
      if 'hf_SI' in raw_data and raw_data['hf_SI']:
          parts = raw_data['hf_SI'].split(',')
          if len(parts) >= 10:
              data['international_silver'] = {
                  'name': 'COMEX白银',
                  'latest': float(parts[0]) if parts[0] else float(parts[2]),
                  'bid': float(parts[2]),
                  'ask': float(parts[3]),
                  'high': float(parts[4]),
                  'low': float(parts[5]),
                  'time': parts[6],
                  'prev_close': float(parts[7]),
                  'unit': '美元/盎司'
              }

      # 离岸人民币
      if 'fx_susdcnh' in raw_data and raw_data['fx_susdcnh']:
          parts = raw_data['fx_susdcnh'].split(',')
          if len(parts) >= 10:
              data['usdcnh'] = {
                  'name': 'USD/CNH',
                  'latest': float(parts[1]),
                  'bid': float(parts[1]),
                  'ask': float(parts[2]),
                  'high': float(parts[5]),
                  'low': float(parts[6]),
                  'prev_close': float(parts[8]),
                  'unit': ''
              }

      return data


  def get_mock_data():
      """模拟数据（用于测试）"""
      return {
          'domestic_gold': {
              'name': '沪金连续',
              'open': 778.50,
              'high': 785.20,
              'low': 775.80,
              'prev_close': 776.00,
              'bid': 782.30,
              'ask': 782.50,
              'latest': 782.40,
              'prev_settle': 776.00,
              'volume': 125680,
              'position': 285430,
              'date': datetime.now().strftime('%Y-%m-%d'),
              'unit': '元/克'
          },
          'domestic_silver': {
              'name': '沪银连续',
              'open': 8250.00,
              'high': 8380.00,
              'low': 8210.00,
              'prev_close': 8230.00,
              'bid': 8350.00,
              'ask': 8355.00,
              'latest': 8352.00,
              'prev_settle': 8230.00,
              'volume': 456200,
              'unit': '元/千克'
          },
          'international_gold': {
              'name': 'COMEX黄金',
              'latest': 3345.60,
              'bid': 3345.40,
              'ask': 3346.20,
              'high': 3380.50,
              'low': 3320.80,
              'time': '04:59:45',
              'prev_close': 3330.00,
              'open': 3335.00,
              'date': datetime.now().strftime('%Y-%m-%d'),
              'unit': '美元/盎司'
          },
          'international_silver': {
              'name': 'COMEX白银',
              'latest': 32.85,
              'bid': 32.83,
              'ask': 32.87,
              'high': 33.20,
              'low': 32.50,
              'time': '04:59:21',
              'prev_close': 32.60,
              'unit': '美元/盎司'
          },
          'usdcnh': {
              'name': 'USD/CNH',
              'latest': 7.1850,
              'bid': 7.1840,
              'ask': 7.1860,
              'high': 7.1950,
              'low': 7.1780,
              'prev_close': 7.1900,
              'unit': ''
          }
      }


  def calc_change_pct(latest, prev):
      """计算涨跌幅"""
      if not prev:
          return 0.0
      return (latest - prev) / prev * 100


  def format_message(data):
      """格式化金价消息"""
      now = datetime.now().strftime("%Y-%m-%d %H:%M")

      lines = [
          f"🪙 金价行情播报 ({now})",
          f"━━━━━━━━━━━━━━━━━━━━",
          f"",
      ]

      # 国内黄金
      if 'domestic_gold' in data:
          g = data['domestic_gold']
          chg = calc_change_pct(g['latest'], g.get('prev_settle', g['prev_close']))
          emoji = "📈" if chg >= 0 else "📉"
          lines.append(f"🇨🇳 {g['name']}")
          lines.append(f"   最新: {g['latest']:.2f} {g['unit']}")
          lines.append(f"   涨跌: {emoji} {chg:+.2f}%")
          lines.append(f"   最高: {g['high']:.2f}  最低: {g['low']:.2f}")
          lines.append(f"   开盘: {g['open']:.2f}  昨收: {g['prev_close']:.2f}")
          lines.append(f"   成交: {g['volume']:,} 手")
          lines.append(f"")

      # 国际黄金
      if 'international_gold' in data:
          g = data['international_gold']
          chg = calc_change_pct(g['latest'], g['prev_close'])
          emoji = "📈" if chg >= 0 else "📉"
          lines.append(f"🇺🇸 {g['name']}")
          lines.append(f"   最新: {g['latest']:.2f} {g['unit']}")
          lines.append(f"   涨跌: {emoji} {chg:+.2f}%")
          lines.append(f"   最高: {g['high']:.2f}  最低: {g['low']:.2f}")
          lines.append(f"   开盘: {g['open']:.2f}  时间: {g['time']}")
          lines.append(f"")

      # 离岸人民币
      if 'usdcnh' in data:
          r = data['usdcnh']
          chg = calc_change_pct(r['latest'], r['prev_close'])
          emoji = "📈" if chg >= 0 else "📉"
          lines.append(f"💱 {r['name']}: {r['latest']:.4f} ({chg:+.2f}%)")
          lines.append(f"")

      # 国内白银（简要）
      if 'domestic_silver' in data:
          s = data['domestic_silver']
          chg = calc_change_pct(s['latest'], s.get('prev_settle', s['prev_close']))
          emoji = "📈" if chg >= 0 else "📉"
          lines.append(f"🥈 {s['name']}: {s['latest']:.0f} {s['unit']} ({emoji} {chg:+.2f}%)")

      # 国际白银（简要）
      if 'international_silver' in data:
          s = data['international_silver']
          chg = calc_change_pct(s['latest'], s['prev_close'])
          emoji = "📈" if chg >= 0 else "📉"
          lines.append(f"🥈 {s['name']}: {s['latest']:.2f} {s['unit']} ({emoji} {chg:+.2f}%)")

      lines.append(f"")
      lines.append(f"━━━━━━━━━━━━━━━━━━━━")
      lines.append(f"📅 更新时间: {now}")

      title = f"🪙 金价行情 ({now})"
      content = '\n'.join(lines)
      return title, content# 
    ==================== 微信推送函数 ====================

  def push_serverchan(key, title, content):
      """Server酱推送"""
      if not key:
          return False, "未配置 ServerChan Key"

      url = f"https://sctapi.ftqq.com/{key}.send"
      data = urllib.parse.urlencode({
          'title': title,
          'desp': content.replace('\n', '\n\n')
      }).encode('utf-8')

      try:
          req = urllib.request.Request(url, data=data, method='POST')
          with urllib.request.urlopen(req, timeout=15) as resp:
              result = json.loads(resp.read().decode('utf-8'))
          if result.get('code') == 0 or result.get('data', {}).get('errno') == 0:
              return True, "Server酱推送成功"
          return False, f"Server酱推送失败: {result}"
      except Exception as e:
          return False, f"Server酱异常: {str(e)}"


  def push_wechat_work(key, content):
      """企业微信机器人推送"""
      if not key:
          return False, "未配置企业微信机器人 Key"

      url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"
      payload = {
          "msgtype": "text",
          "text": {
              "content": content
          }
      }
      data = json.dumps(payload, ensure_ascii=False).encode('utf-8')

      try:
          req = urllib.request.Request(url, data=data, headers={
              'Content-Type': 'application/json'
          }, method='POST')
          with urllib.request.urlopen(req, timeout=15) as resp:
              result = json.loads(resp.read().decode('utf-8'))
          if result.get('errcode') == 0:
              return True, "企业微信推送成功"
          return False, f"企业微信推送失败: {result}"
      except Exception as e:
          return False, f"企业微信异常: {str(e)}"


  def push_bark(key, title, content):
      """Bark iOS推送"""
      if not key:
          return False, "未配置 Bark Key"

      body = urllib.parse.quote(content)
      url = f"https://api.day.app/{key}/{urllib.parse.quote(title)}/{body}?group=金价"

      try:
          req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
          with urllib.request.urlopen(req, timeout=15) as resp:
              result = json.loads(resp.read().decode('utf-8'))
          if result.get('code') == 200:
              return True, "Bark推送成功"
          return False, f"Bark推送失败: {result}"
      except Exception as e:
          return False, f"Bark异常: {str(e)}"


  def push_plus(token, title, content):
      """PushPlus 微信推送"""
      if not token:
          return False, "未配置 PushPlus Token"

      url = "https://www.pushplus.plus/send"
      payload = {
          "token": token,
          "title": title,
          "content": content,
          "template": "txt"
      }
      data = json.dumps(payload, ensure_ascii=False).encode('utf-8')

      try:
          req = urllib.request.Request(url, data=data, headers={
              'Content-Type': 'application/json'
          }, method='POST')
          with urllib.request.urlopen(req, timeout=15) as resp:
              result = json.loads(resp.read().decode('utf-8'))
          if result.get('code') == 200:
              return True, "PushPlus推送成功"
          return False, f"PushPlus推送失败: {result.get('msg', result)}"
      except Exception as e:
          return False, f"PushPlus异常: {str(e)}"


  # ==================== 主程序 ====================

  def main():
      print("=" * 40)
      print("🪙 金价推送脚本启动")
      print("=" * 40)

      # 1. 获取金价
      print("\n📡 正在获取金价数据...")

      if USE_MOCK_DATA:
          print("⚠️ 测试模式：使用模拟数据")
          data = get_mock_data()
      else:
          raw = fetch_sina_quotes(['AU0', 'AG0', 'hf_GC', 'hf_SI', 'fx_susdcnh'])

          if '_error' in raw:
              print(f"❌ 获取数据失败: {raw['_error']}")
              print("\n💡 提示：可设置 USE_MOCK_DATA = True 使用模拟数据测试推送")
              sys.exit(1)

          data = parse_gold_data(raw)

          if not data:
              print("❌ 解析数据失败，返回空结果")
              print("\n💡 提示：可设置 USE_MOCK_DATA = True 使用模拟数据测试推送")
              sys.exit(1)

      print(f"✅ 金价数据获取成功")

      # 2. 格式化消息
      title, content = format_message(data)
      print(f"\n📋 消息内容:\n{'-'*40}")
      print(content)
      print('-'*40)

      # 3. 推送到微信
      print("\n📤 开始推送...")
      pushed = False

      if SERVERCHAN_KEY:
          ok, msg = push_serverchan(SERVERCHAN_KEY, title, content)
          print(f"   Server酱: {'✅' if ok else '❌'} {msg}")
          pushed = pushed or ok

      if WECHAT_WORK_KEY:
          ok, msg = push_wechat_work(WECHAT_WORK_KEY, content)
          print(f"   企业微信: {'✅' if ok else '❌'} {msg}")
          pushed = pushed or ok

      if BARK_KEY:
          ok, msg = push_bark(BARK_KEY, title, content)
          print(f"   Bark: {'✅' if ok else '❌'} {msg}")
          pushed = pushed or ok

      if PUSHPLUS_TOKEN:
          ok, msg = push_plus(PUSHPLUS_TOKEN, title, content)
          print(f"   PushPlus: {'✅' if ok else '❌'} {msg}")
          pushed = pushed or ok

      if not pushed:
          print("\n⚠️ 没有配置任何推送方式，请在脚本中配置：")
          print("   - SERVERCHAN_KEY (Server酱)")
          print("   - WECHAT_WORK_KEY (企业微信机器人)")
          print("   - BARK_KEY (Bark iOS)")
          print("   - PUSHPLUS_TOKEN (PushPlus)")
      else:
          print("\n🎉 金价推送完成！")


  if __name__ == '__main__':
      main()
