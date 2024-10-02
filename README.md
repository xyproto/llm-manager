# llm-manager

A utility written in Python 3 for querying and managing keys and values in `~/.config/llm-manager/llm.conf` and `/etc/llm.conf`.

**The idea is that if an editor needs to use the best available LLM model for code completion, it can run this to get the user-configured answer, with a fallback on the system defaults:**

```bash
$ llm-manager code-completion
deepseek-coder-v2:236b
```

This way, the user can install and configure the best Ollama model that their laptop and/or Ollama server (defined with `OLLAMA_HOST`) can support.

## Example use

Set the default `text-generation` model to `gemma2:2b`:

```bash
$ llm-manager set text-generation gemma2:2b
```

Get the current `text-generation` model

```bash
$ llm-manager get text-generation
gamma2:2b
```

A shortcut:

```bash
$ llm-manager text-generation
gemma2:2b
```

Changing the `text-generation` model to `llama3.2` and the `3b` tag:

```bash
$ llm-manager set text-generation llama3.2:3b
```

Get the current `text-generation` model:

```bash
$ llm-manager text-generation
llama3.2:3b
```

## Default values

The default values for the current version of `llm-manager` and `/etc/llm.conf` are:

| Task            | Model               |
|-----------------|---------------------|
| chat            | llama3.2:3b         |
| code-completion | deepseek-coder:1.3b |
| test            | tinyllama:1b        |
| text-generation | gemma2:2b           |
| tool-use        | llama3.2:3b         |
| translation     | mixtral:8x7b        |
| vision          | llava:7b            |

The default configuration may change over time as better models become available.

For now, relatively small models are chosen, so that more people can use them, even without a GPU.

Here is the default configuration file, `llm.conf`:

```configuration
# For chatting
chat=llama3.2:3b

# For code completion / tab autocompletion
code-completion=deepseek-coder:1.3b

# A small model, for quick tests
test=tinyllama:1b

# Text generation
text-generation=gemma2:2b

# Tool use and function calling
tool-use=llama3.2:3b

# For translating text (not single words, though)
translation=mixtral:8x7b

# Vision and image detection
vision=llava:7b
```

## General info

* Version: 1.2.0
* License: BSD-3
* Author: Alexander F. Rødseth &lt;xyproto@archlinux.org&gt;
