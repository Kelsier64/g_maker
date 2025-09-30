import requests
import json
import time
import io
import sys

def main():
    # ComfyUI 服务器的地址，如果是本地就是 127.0.0.1:8188
    server_address = "127.0.0.1:8188"
    # 1. 加载你保存的工作流 JSON 文件
    workflow_file_path = "static/kj720p.json"
    
    with open(workflow_file_path, 'r', encoding='utf-8') as f:
        workflow_data = json.load(f)

    # 2. 修改工作流中的参数
    # 这是最关键的一步！你需要知道你要修改的节点在 JSON 中的位置。
    # 在 ComfyUI 界面中，双击节点，查看 "Node name" 或者标题。
    # workflow_data 是一个字典，其主键是节点的唯一ID，值是节点的配置。

    # 方法一：手动查找并修改（推荐，精确控制）
    # 遍历所有节点，找到我们关心的节点（例如 KSampler 和 CLIPTextEncode）
    # for node_id, node_config in workflow_data.items():
    #     # 根据节点的 "class_type" 来定位
    #     if node_config["class_type"] == "KSampler":
    #         # 修改种子
    #         node_config["inputs"]["seed"] = 123456
    #     # 找到正面提示词输入节点（通常是 "CLIP Text Encode (Prompt)" 类）
    #     if node_config["class_type"] == "CLIPTextEncode":
    #         # 你可能需要根据你的工作流结构来判断哪个是正面，哪个是负面
    #         # 一个简单的方法是查看节点的 ‘_meta’ 标题（如果保存了的话），或者通过连接关系判断
    #         # 这里假设第一个 CLIPTextEncode 节点是正面提示词
    #         node_config["inputs"]["text"] = "masterpiece, best quality, 1girl, beautiful, in a garden"
    #         # 为了避免修改到负面提示词节点，我们可以修改一次后就 break 或者用更精确的判断
    #         break # 这里只是示例，你可能需要修改多个节点

    # 方法二（更稳健）：在保存工作流前，为关键节点起一个唯一的标题
    # 在 ComfyUI 界面中，双击节点，在 "Node name" 字段输入一个易记的名字，如 "my_sampler", "positive_prompt"。
    # 保存工作流后，JSON 中节点的 ‘_meta’ 字段会记录这个标题，方便你查找。
    # 例如：
    # for node_id, node_config in workflow_data.items():
    #     meta = node_config.get("_meta", {})
    #     title = meta.get("title")
    #     if title == "positive_prompt":
    #         node_config["inputs"]["text"] = "你的新提示词"
    #     elif title == "my_sampler":
    #         node_config["inputs"]["seed"] = 789012

    # 3. 准备 API 请求
    prompt_api_url = f"http://{server_address}/prompt"
    # 构造 API 需要的 payload
    payload = {
        "prompt": workflow_data, # 将修改后的工作流数据作为 prompt 发送
        # "client_id": "你的客户端ID" # 可选，用于 WebSocket 通信，这里我们用简单轮询
    }

    # 4. 发送请求，触发工作流执行
    print("正在向 ComfyUI 提交工作流...")
    try:
        response = requests.post(prompt_api_url, json=payload)
        response.raise_for_status() # 检查请求是否成功
        result = response.json()
        # 获取队列任务的 ID
        prompt_id = result['prompt_id']
        print(f"工作流已提交，任务 ID: {prompt_id}")
    except requests.exceptions.RequestException as e:
        print(f"提交工作流失败: {e}")
        sys.exit(1)

    # 5. 轮询检查执行状态并获取结果
    history_api_url = f"http://{server_address}/history"
    output_images = []

    print("等待任务完成...", end='')
    while True:
        time.sleep(1) # 每秒检查一次
        print('.', end='', flush=True) # 打印进度点

        # 查询历史记录，根据 prompt_id 获取任务结果
        response = requests.get(history_api_url)
        history = response.json()
        
        if prompt_id in history:
            # 任务完成了！
            print("\n任务完成！")
            result_data = history[prompt_id]
            outputs = result_data.get('outputs', {})

            # 遍历所有有输出的节点，找到生成的 GIF
            for node_id, node_output in outputs.items():
                if 'gifs' in node_output:
                    for gif_info in node_output['gifs']:
                        # 构建 GIF 的完整 URL
                        gif_filename = gif_info['filename']
                        gif_url = f"http://{server_address}/view?filename={gif_filename}&subfolder={gif_info.get('subfolder', '')}&type={gif_info.get('type', 'output')}"
                        # 下载 GIF
                        gif_response = requests.get(gif_url)
                        # Save video to local file
                        output_path = f"output_{prompt_id}_{len(output_images)+1}.mp4"
                        with open(output_path, 'wb') as f:
                            f.write(gif_response.content)
                        output_images.append(output_path)
                        print(f"视频已保存至: {output_path}")
            break # 退出轮询循环

    print(f"共生成 {len(output_images)} 张图片。")

if __name__ == "__main__":
    main()