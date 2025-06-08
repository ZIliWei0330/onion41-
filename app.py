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
           "请将以下文本分为九层逐层膨胀意义，每层风格必须发生变化：\n"
    "每层前加中文序号（如“一、二、三、四、五、六、七、八、九”），不要用阿拉伯数字。\n"
    "第1层用极简叙述，10字以内，尽量直接；\n"
    "第2层加入一个简短比喻或象征，20字以内；\n"
    "第3层用富有画面感的诗意语言，30字左右；\n"
    "第4层可以用哲理小品、人生感慨，50字左右；\n"
    "第5层以故事化、寓言式扩展，70字以内；\n"
    "第6层用抽象化/神秘主义/意识流写法，90字以内；\n"
    "第7层可以加入荒谬或离经叛道的设定（如宇宙、宗教、外星人等），110字以内；\n"
    "第8层允许疯狂跳跃、夸张、幽默，140字以内；\n"
    "第9层必须荒谬、操蛋、与前文相关但极度跳脱，比如“所以最后我只想多吃点烧烤”或“其实意义全在土豆丝里”，并且可以故意收尾反高潮；\n"
    "每层只写一遍序号和内容，禁止英文，禁止Markdown。\n"
    "文本内容：“{text}”"
        ).format(text=text)
    else:  # collapse
        prompt = (
              "请将以下内容分为九层逐层压缩，每层要明显风格变化，而不只是缩短字数：\n"
    "每层前加中文序号（如“一、二、三、四、五、六、七、八、九”），不要用阿拉伯数字。\n"
    "第1层用学术/评论腔长篇复述（约90字），保留细节和分析；\n"
    "第2层用“文艺/诗意”风格重述，允许比喻和象征，突出画面感（约70字）；\n"
    "第3层用“口语化自述/碎碎念”风格（50字），加入个人态度/情绪；\n"
    "第4层用“网络土味/段子/吐槽”风格，加入流行语或反差（30字）；\n"
    "第5~6层可以随便编造内容、引入完全不搭边的比喻/笑话（20字以内）；\n"
    "第7~8层用最短的语句、网络热词、废话文学、自嘲、甚至胡说八道（10字）；\n"
    "第9层必须彻底崩坏、发疯、反高潮，比如“其实我想吃炸鸡”、“谁懂啊，饿死了”、“人生意义就是烧烤摊”、或胡说八道但和上文相关。\n"
    "每层只写一遍序号和内容，风格必须随层级大幅变化，禁止英文，禁止Markdown。\n"
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
            "学习失败，洋葱都剥不动，味道全跑了。",
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
            "学习失败，洋葱都剥不动，味道全跑了。",
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