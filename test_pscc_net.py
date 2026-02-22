"""
测试 PSCC-Net 模型加载和检测功能
"""
import os
import sys

# 添加项目根目录到路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

def test_model_loading():
    """测试模型加载"""
    print("=" * 50)
    print("测试 PSCC-Net 模型加载")
    print("=" * 50)
    
    try:
        from app.services.model_detection import PSCC_NET_AVAILABLE, get_model_instance
        from app.utils.config import PSCC_NET_MODEL_PATH
        
        print(f"PSCC-Net 可用: {PSCC_NET_AVAILABLE}")
        print(f"模型路径: {PSCC_NET_MODEL_PATH}")
        print(f"模型文件存在: {os.path.exists(PSCC_NET_MODEL_PATH)}")
        
        if PSCC_NET_AVAILABLE and get_model_instance is not None:
            print("\n尝试加载模型实例...")
            model = get_model_instance(model_path=PSCC_NET_MODEL_PATH)
            print(f"模型设备: {model.device}")
            print(f"模型已加载: {model.model is not None}")
            print("[OK] 模型加载成功！")
        else:
            print("[WARNING] PSCC-Net 模块不可用，将使用占位实现")
            
    except Exception as e:
        import traceback
        print(f"[ERROR] 测试失败: {str(e)}")
        print(traceback.format_exc())


def test_detection_function():
    """测试检测函数"""
    print("\n" + "=" * 50)
    print("测试检测函数")
    print("=" * 50)
    
    try:
        from app.services.model_detection import detect_with_model
        
        # 检查是否有测试图片
        test_image = os.path.join(backend_dir, "uploads")
        if os.path.exists(test_image):
            # 查找第一个图片文件
            for file in os.listdir(test_image):
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    test_image_path = os.path.join(test_image, file)
                    print(f"\n使用测试图片: {test_image_path}")
                    
                    is_tampered, tamper_ratio, tampered_regions, tamper_mask = detect_with_model(
                        test_image_path,
                        confidence_threshold=0.5
                    )
                    
                    print(f"检测结果:")
                    print(f"  - 是否被篡改: {is_tampered}")
                    print(f"  - 篡改比例: {tamper_ratio:.4f}")
                    print(f"  - 篡改区域数量: {len(tampered_regions)}")
                    print(f"  - 掩码形状: {tamper_mask.shape if tamper_mask is not None else None}")
                    print("[OK] 检测函数测试成功！")
                    return
                    
        print("[WARNING] 未找到测试图片，跳过检测测试")
        
    except Exception as e:
        import traceback
        print(f"[ERROR] 检测测试失败: {str(e)}")
        print(traceback.format_exc())


if __name__ == "__main__":
    test_model_loading()
    test_detection_function()
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)

