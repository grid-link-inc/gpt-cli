# import pytest
# from gptcli.gpt_interfaces.wrapper.wrapper import WrapperGlobalArgs, init_wrapper


# @pytest.mark.parametrize(
#     "args,custom_wrappers,expected_config",
#     [
#         (
#             WrapperGlobalArgs("dev"),
#             {},
#             {},
#         ),
#         (
#             WrapperGlobalArgs("dev", model="gpt-4"),
#             {},
#             {"model": "gpt-4"},
#         ),
#         (
#             WrapperGlobalArgs("dev", temperature=0.5, top_p=0.5),
#             {},
#             {"temperature": 0.5, "top_p": 0.5},
#         ),
#         (
#             WrapperGlobalArgs("dev"),
#             {
#                 "dev": {
#                     "model": "gpt-4",
#                 },
#             },
#             {"model": "gpt-4"},
#         ),
#         (
#             WrapperGlobalArgs("dev", model="gpt-4"),
#             {
#                 "dev": {
#                     "model": "gpt-3.5-turbo",
#                 },
#             },
#             {"model": "gpt-4"},
#         ),
#         (
#             WrapperGlobalArgs("custom"),
#             {
#                 "custom": {
#                     "model": "gpt-4",
#                     "temperature": 0.5,
#                     "top_p": 0.5,
#                     "messages": [],
#                 },
#             },
#             {"model": "gpt-4", "temperature": 0.5, "top_p": 0.5},
#         ),
#         (
#             WrapperGlobalArgs(
#                 "custom", model="gpt-3.5-turbo", temperature=1.0, top_p=1.0
#             ),
#             {
#                 "custom": {
#                     "model": "gpt-4",
#                     "temperature": 0.5,
#                     "top_p": 0.5,
#                     "messages": [],
#                 },
#             },
#             {"model": "gpt-3.5-turbo", "temperature": 1.0, "top_p": 1.0},
#         ),
#     ],
# )
# def test_init_wrapper(args, custom_wrappers, expected_config):
#     wrapper = init_wrapper(args, custom_wrappers)
#     assert wrapper.config.get("model") == expected_config.get("model")
#     assert wrapper.config.get("temperature") == expected_config.get("temperature")
#     assert wrapper.config.get("top_p") == expected_config.get("top_p")
