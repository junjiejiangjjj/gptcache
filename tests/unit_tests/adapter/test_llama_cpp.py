import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from tempfile import TemporaryDirectory

from gptcache import Cache
from gptcache.processor.pre import get_prompt
from gptcache.manager.factory import manager_factory
from gptcache.embedding import Onnx

question = "test_llama_cpp"
expect_answer = "hello world"
onnx = Onnx()

class MockLlama:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return {
            "choices": [
                {
                    "finish_reason": "stop",
                    "index": 0,
                    "text": expect_answer,
                }
            ],
            "created": 1677825456,
            "id": "chatcmpl-6ptKqrhgRoVchm58Bby0UvJzq2ZuQ",
            "model": "llam_cpp",
            "object": "chat.completion",
            "usage": {
                "completion_tokens": 301,
                "prompt_tokens": 36,
                "total_tokens": 337
            }
        }


class MockStreamLlama:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        yield {
            "choices": [
                {
                    "finish_reason": "stop",
                    "index": 0,
                    "text": expect_answer,
                }
            ],
            "created": 1677825456,
            "id": "chatcmpl-6ptKqrhgRoVchm58Bby0UvJzq2ZuQ",
            "model": "llam_cpp",
            "object": "chat.completion",
            "usage": {
                "completion_tokens": 301,
                "prompt_tokens": 36,
                "total_tokens": 337
            }
        }


mock_module = MagicMock()
sys.modules['llama_cpp'] = mock_module


class TestLlama(unittest.TestCase):
    def test_llama_cpp(self):
        mock_module.Llama = MockLlama
        with TemporaryDirectory(dir="./") as root:
            m = manager_factory('sqlite,faiss,local', data_dir=root, vector_params={"dimension": onnx.dimension})
            llm_cache = Cache()
            llm_cache.init(
                pre_embedding_func=get_prompt,
                data_manager=m,
                embedding_func=onnx.to_embeddings
            )

            with patch('gptcache.utils.import_llama_cpp_python'):
                from gptcache.adapter.llamacpp import LlamaCpp
                llm = LlamaCpp('model.bin')
                answer = llm(prompt=question, cache_obj=llm_cache)
                assert expect_answer == answer['choices'][0]['text']

                answer2 = llm(prompt=question, cache_obj=llm_cache)
                assert answer2['gptcache'] is True
                assert expect_answer == answer2['choices'][0]['text']                

                llm(prompt=question, cache_obj=llm_cache, stream=True, stop=['\n'])

        with TemporaryDirectory(dir="./") as root:
            m = manager_factory('sqlite,faiss,local', data_dir=root, vector_params={"dimension": onnx.dimension})
            llm_cache = Cache()
            llm_cache.init(
                pre_embedding_func=get_prompt,
                data_manager=m,
                embedding_func=onnx.to_embeddings
            )
        
            with patch('gptcache.utils.import_llama_cpp_python'):
                from gptcache.adapter.llamacpp import LlamaCpp
                llm = LlamaCpp('model.bin', stop=['\n'])
                llm._llm = MockStreamLlama()

                with self.assertRaises(ValueError):
                    llm(prompt=question, cache_obj=llm_cache, stream=True, stop=['\n'])
                answer = llm(prompt=question, cache_obj=llm_cache, stream=True)
                for item in answer:
                    self.assertEqual(item['choices'][0]['text'], expect_answer)

                answer2 = llm(prompt=question, cache_obj=llm_cache, stream=True)[0]
                assert answer2['gptcache'] is True
                assert expect_answer == answer2['choices'][0]['text']
