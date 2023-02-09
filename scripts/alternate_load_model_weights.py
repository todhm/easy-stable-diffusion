import os
import threading
import time
from shutil import rmtree
from subprocess import call
from tempfile import mkdtemp
from typing import Callable

from modules import scripts, sd_models, shared

load_model_weights: Callable


def alternate_load_model_weights(model, checkpoint_info: sd_models.CheckpointInfo, *args, **kwargs):
    print('모델을 임시 폴더에 복사합니다.')

    # rsync 로 사용자에게 모델 복사까지 남은 시간 보여주기
    temp_dir = mkdtemp()
    copied_checkpoint_file = os.path.join(temp_dir, checkpoint_info.name)
    call(['rsync', '-aP', checkpoint_info.filename, copied_checkpoint_file])

    print(f'성공적으로 {copied_checkpoint_file} 경로에 복사했습니다.')

    try:
        sd = load_model_weights(
            model,
            sd_models.CheckpointInfo(copied_checkpoint_file),
            *args, **kwargs
        )
    finally:
        print('임시 모델 파일을 제거합니다.')
        rmtree(temp_dir, True)

    return sd


def on_app_started(*args, **kwargs):
    # TODO: VAE 같은 다른 모델 선택할 때도 메모리 밀어줘야함

    def save_and_exit():
        # 클라이언트에게 결과를 반환하지 않으면 설정을 다시 바꿀 수 없게 되어버림
        # 새 스레드에서 1초 대기 후 프로세스를 종료해 인터페이스가 먹통되지 않도록 우회함
        print('설정을 저장하고 프로세스를 종료한 뒤 원클릭 코랩을 통해 프로세스를 재시작합니다.')
        time.sleep(1)

        # 설정 파일 저장한 뒤 프로세스 종료
        shared.opts.save(shared.config_filename)
        os._exit(0)

    shared.opts.onchange(
        'sd_model_checkpoint',
        lambda: threading.Thread(target=save_and_exit).start(),
        call=False)


scripts.script_callbacks.on_app_started(on_app_started)


if not sd_models.load_model_weights == alternate_load_model_weights:
    print('수정된 load_model_weights 메소드를 적용했습니다')
    load_model_weights = sd_models.load_model_weights
    sd_models.load_model_weights = alternate_load_model_weights
