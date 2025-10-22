"""
메모리 사용량 모니터링 및 디버깅 도구
"""
import psutil
import os
import gc
import tracemalloc
from functools import wraps
import time

def get_memory_usage():
    """현재 프로세스의 메모리 사용량을 반환 (MB 단위)"""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return {
        'rss': mem_info.rss / 1024 / 1024,  # 실제 메모리 사용량
        'vms': mem_info.vms / 1024 / 1024,  # 가상 메모리 사용량
        'percent': process.memory_percent()  # 전체 메모리 대비 퍼센트
    }

def print_memory_usage(label=""):
    """메모리 사용량 출력"""
    mem = get_memory_usage()
    print(f"[메모리 {label}]")
    print(f"  - RSS: {mem['rss']:.1f} MB")
    print(f"  - VMS: {mem['vms']:.1f} MB")
    print(f"  - 전체 대비: {mem['percent']:.1f}%")
    print()

def memory_profiler(func):
    """함수 실행 전후 메모리 사용량을 출력하는 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 가비지 컬렉션 수행
        gc.collect()
        
        # 실행 전 메모리
        mem_before = get_memory_usage()
        print(f"\n{'='*60}")
        print(f"함수: {func.__name__}")
        print(f"{'='*60}")
        print(f"실행 전 - RSS: {mem_before['rss']:.1f} MB, Percent: {mem_before['percent']:.1f}%")
        
        # 함수 실행
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        
        # 실행 후 메모리
        mem_after = get_memory_usage()
        mem_diff = mem_after['rss'] - mem_before['rss']
        
        print(f"실행 후 - RSS: {mem_after['rss']:.1f} MB, Percent: {mem_after['percent']:.1f}%")
        print(f"메모리 증가: {mem_diff:+.1f} MB")
        print(f"실행 시간: {elapsed_time:.2f}초")
        print(f"{'='*60}\n")
        
        return result
    return wrapper

def start_memory_tracking():
    """tracemalloc을 사용한 상세 메모리 추적 시작"""
    tracemalloc.start()
    print("✅ 메모리 추적 시작")

def show_top_memory_usage(limit=10):
    """메모리를 가장 많이 사용하는 코드 라인 출력"""
    if not tracemalloc.is_tracing():
        print("❌ 메모리 추적이 시작되지 않았습니다. start_memory_tracking()을 먼저 호출하세요.")
        return
    
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    
    print(f"\n{'='*60}")
    print(f"메모리를 가장 많이 사용하는 Top {limit} 라인")
    print(f"{'='*60}")
    
    for index, stat in enumerate(top_stats[:limit], 1):
        print(f"{index}. {stat.filename}:{stat.lineno}")
        print(f"   크기: {stat.size / 1024 / 1024:.1f} MB")
        print(f"   할당 횟수: {stat.count}")
        print()

def compare_memory_snapshots(snapshot1, snapshot2, limit=10):
    """두 시점의 메모리 스냅샷을 비교"""
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    
    print(f"\n{'='*60}")
    print(f"메모리 증가량 Top {limit}")
    print(f"{'='*60}")
    
    for index, stat in enumerate(top_stats[:limit], 1):
        print(f"{index}. {stat.filename}:{stat.lineno}")
        print(f"   크기 증가: {stat.size_diff / 1024 / 1024:+.1f} MB")
        print(f"   할당 증가: {stat.count_diff:+}")
        print()

def check_streamlit_cache():
    """Streamlit 캐시 상태 확인"""
    try:
        import streamlit as st
        cache_stats = st.cache_data.clear.__doc__
        print("Streamlit 캐시 함수 사용 중")
    except:
        print("Streamlit이 없거나 캐시 확인 불가")

def force_garbage_collection():
    """강제로 가비지 컬렉션 수행 및 결과 출력"""
    mem_before = get_memory_usage()
    print("가비지 컬렉션 수행 중...")
    
    collected = gc.collect()
    
    mem_after = get_memory_usage()
    mem_freed = mem_before['rss'] - mem_after['rss']
    
    print(f"수집된 객체: {collected}개")
    print(f"해제된 메모리: {mem_freed:.1f} MB")
    print_memory_usage("GC 후")

if __name__ == "__main__":
    # 테스트
    print_memory_usage("시작")
    
    # 메모리를 사용하는 예제
    @memory_profiler
    def test_function():
        import numpy as np
        # 큰 배열 생성 (약 76MB)
        arr = np.zeros((1000, 10000))
        return arr.shape
    
    result = test_function()
    print(f"결과: {result}")
    
    force_garbage_collection()
    print_memory_usage("종료")

