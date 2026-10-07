# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""Graba muestras de la voz (cada ánimo, el respiro en textos largos y el confeti) en .wav, para escucharlas.

    python dev/muestras_voz.py CARPETA_DE_SALIDA [RUTA_DE_LA_VOZ.onnx]
"""
import json
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402
import efectos  # noqa: E402
import voz as V  # noqa: E402

MUESTRAS = [
    ('01-normal', '', '', '¡Pedido nuevo! A ver… Leo mascota.py y después busco dónde se rompe el globo.'),
    ('02-largo-con-respiro', '', '',
     'Encontré el error en el globo: la fuente nueva no tenía los acentos bien y entonces el texto se cortaba '
     'cuando era largo. Ahora pruebo con la otra fuente, que sí los tiene. Si anda, después reviso el resto de '
     'las ventanas, porque puede que pase lo mismo en la configuración.'),
    ('03-contento-confeti', 'contento', 'confeti', '¡Golazo! ¡Listo! Me salió redondo.'),
    ('04-fiesta', 'contento', 'fiesta', '¡Por fin! ¡Lo logramos! Qué maratón.'),
    ('05-enojado', 'enojado', '', '¡No puede ser, che! ¡Esto me tiene podrido! Dale, andá de una vez.'),
    ('06-cansado', 'cansado', '', 'Uff… este proyecto tiene tela para cortar. Pero vamos bien igual.'),
    ('07-triste-memoria', 'triste', '', 'Hoy recordamos a los veteranos y a los caídos en Malvinas.'),
    ('08-sorpresa', 'sorpresa', '', '¡Epa! Algo no cerró. Ya lo miro.'),
    ('09-curiosidad', '', '', '¿Sabías que…? Belgrano murió pobre: le pagó al médico con su reloj.'),
]


def main():
    salida = Path(sys.argv[1])
    salida.mkdir(parents=True, exist_ok=True)
    cfg = dict(config.POR_DEFECTO)
    if len(sys.argv) > 2:
        cfg['modelo'] = sys.argv[2]
    from piper import PiperVoice
    from piper.config import PiperConfig
    import onnxruntime
    v = V.Voz.__new__(V.Voz)
    v.cfg = cfg
    datos = json.loads(Path(cfg['modelo'] + '.json').read_text(encoding='utf-8'))
    v.voz = PiperVoice(config=PiperConfig.from_dict(datos),
                       session=onnxruntime.InferenceSession(cfg['modelo'], providers=['CPUExecutionProvider']))
    v.sr = v.voz.config.sample_rate
    for nombre, animo, efecto, texto in MUESTRAS:
        tono = float(cfg['tono']) * V.ANIMOS[animo][0]
        audio, sr = v._daniela(texto, tono, animo)
        if efecto:
            audio, _ = efectos.mezclar(efectos.generar(efecto, sr), audio, sr)
        audio = np.clip(audio * 0.9, -1, 1)
        with wave.open(str(salida / f'{nombre}.wav'), 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(int(sr * tono))          # igual que al reproducir: así sube el tono
            w.writeframes((audio * 32767).astype('<i2').tobytes())
        print(nombre, f'{len(audio) / (sr * tono):.1f} s')


if __name__ == '__main__':
    main()
