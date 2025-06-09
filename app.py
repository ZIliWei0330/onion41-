from flask import Flask, request, jsonify, Response
import time
import random
import os

import openai

openai.api_key = os.environ.get('OPENAI_API_KEY')

app = Flask(__name__, static_folder='static', static_url_path='')

def get_lmstudio_inference(text, mode='inflate'):
    if mode == 'inflate':
        prompt = (
            "请将以下文本分为九层递进，每一层都像当代艺术家在展览开幕式上做阐述一样，"
            "用极度装腔、学术、抽象、玄乎、诗意、隐喻、复杂难懂的语言写作，且每一层风格、修辞、叙述角度递进不同。"
            "层层围绕‘身份、假象、剥洋葱、钓鱼、被钓’等主题推进，结尾可极度自嘲或荒谬。"
            "要求每层有中文序号（如“一、二…”），不可用阿拉伯数字，每层只写一遍序号和内容，禁止英文、禁止Markdown。"
            "文本内容：“{text}”"
        ).format(text=text)
    else:  # deflate
        prompt = (
            "请将以下内容分为九层递进，每一层用最极端通俗、土味、网络、吐槽、讽刺的风格转译，像市井大爷调侃艺术展或生活。"
            "每层递减，结尾可自嘲、反高潮、网络流行语。"
            "每层有中文序号（如“一、二…”），每层只写一遍序号和内容，禁止英文、禁止Markdown。"
            "文本内容：“{text}”"
        ).format(text=text)

    try:
        print("[DEBUG] 即将请求 OpenAI API")
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1800,
            temperature=0.7,
            stream=True
        )
        import re
        buffer = ""
        for chunk in response:
            delta = chunk['choices'][0]['delta']
            if 'content' in delta:
                buffer += delta['content']
                # 尝试分割成行，yield 完整的层
                lines = re.split(r'[\r\n]+', buffer)
                # 保留最后一行不完整的部分
                buffer = lines[-1]
                for line in lines[:-1]:
                    line = line.strip()
                    if not line:
                        continue
                    # 过滤掉可能的自我思考句子
                    if re.search(r"(我得理解|用户希望|我要先|需要注意|总结一下)", line):
                        continue
                    print(f"[DEBUG] yield line: {line}")
                    yield line.encode("utf-8")
        # 最后剩余的内容也输出
        final_line = buffer.strip()
        if final_line and not re.search(r"(我得理解|用户希望|我要先|需要注意|总结一下)", final_line):
            print(f"[DEBUG] yield final line: {final_line}")
            yield final_line.encode("utf-8")
    except Exception as e:
        import traceback
        traceback.print_exc()
        fallback_text = [
            "装腔失败，艺术家流泪下班。",
            "这洋葱又臭又辣，剥了半天没剥出层次感。",
            "老板说了，剥洋葱要有耐心，可你们这操作真是离谱。",
            "再剥下去眼泪都流出来了，别说味道了，连形状都不对。",
            "其实这洋葱就是个洋葱，别想太多，吃了就完事儿。"
        ]
        for line in fallback_text:
            print(f"[DEBUG] fallback yield line: {line}")
            yield line.encode("utf-8")

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    print("收到 /analyze 请求")
    try:
        mode = request.args.get('mode', 'inflate')
        if request.method == 'GET':
            text = request.args.get('text', 'Default test text')
        else:
            text = request.json.get('text', 'Default test text')
        print(f"收到文本：{text}，模式：{mode}")
        analysis_generator = get_lmstudio_inference(text, mode=mode)
        print("开始分析并流式返回结果")
        def generate():
            print("[DEBUG] yield initial message: 正在剥开洋葱......")
            yield "data: 正在剥开洋葱......\n\n".encode("utf-8")
            time.sleep(5)
            print("[DEBUG] yield message: 洋葱已剥开！让我闻一下什么味道！")
            yield "data: 洋葱已剥开！让我闻一下什么味道！\n\n".encode("utf-8")
            time.sleep(3)
            for line in analysis_generator:
                # line is bytes already from get_lmstudio_inference
                decoded_line = line.decode("utf-8")
                print(f"[DEBUG] yield data: {decoded_line}")
                yield f"data: {decoded_line}\n\n".encode("utf-8")
                time.sleep(2)
        return Response(generate(), mimetype='text/event-stream')
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("OpenAI调用异常：", e)  # 加这行
        fallback_text = [
            "装腔失败，艺术家流泪下班。",
            "这洋葱又臭又辣，剥了半天没剥出层次感。",
            "老板说了，剥洋葱要有耐心，可你们这操作真是离谱。",
            "再剥下去眼泪都流出来了，别说味道了，连形状都不对。",
            "其实这洋葱就是个洋葱，别想太多，吃了就完事儿。"
        ]
        def fallback_generate():
            for line in fallback_text:
                print(f"[DEBUG] fallback yield line: {line}")
                yield f"data: {line}\n\n".encode("utf-8")
        error_msg = f"错误：{str(e)}"
        print("analyze 捕获异常：", error_msg)
        def error_generate():
            print(f"[DEBUG] error yield message: {error_msg}")
            yield f"data: {error_msg}\n\n".encode("utf-8")
            print("[DEBUG] error yield message: 洋葱剥不开，哭着也要吃完它。")
            yield "data: 洋葱剥不开，哭着也要吃完它。\n\n".encode("utf-8")
        return Response(fallback_generate(), mimetype='text/event-stream') if not error_msg else Response(error_generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))