nnoremap gd ^r+ddGp<c-o>:w<cr>
nnoremap gc ^r-ddGp<c-o>:w<cr>

function! TODOAleGetCommand(buffer) abort
    return 'python3 /Users/zloy/dev/vim-todo/reminder.py --verify --file %t' 
endfunction

function TODOAleHandle(buffer, lines) abort
    let l:patterns = [
    \ '\vERROR (.*) at line (\d+) col (\d+)'
    \ ]
    let l:output = []

    for l:match in ale#util#GetMatches(a:lines, l:patterns)
        let l:args = {
        \   'text': l:match[1],
        \   'lnum': l:match[2] + 0,
        \   'col': l:match[3] + 0,
        \ }
        call add(l:output, l:args)
    endfor
    return l:output
endfunction

call ale#linter#Define("todo", {
\   'name': 'python/todo.py',
\   'output_stream': 'stderr',
\   'executable': 'python3',
\   'command_callback': 'TODOAleGetCommand',
\   'callback': 'TODOAleHandle',
\})
