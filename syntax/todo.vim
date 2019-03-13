if exists("b:current_syntax")
  finish
endif

syn clear

syn match person /\v\@\w+(\s\u\w*)?>/
syn match task /\v<T\d+>/
syn match diff /\v<D\d+>/
syn match atag /\v#\w+>/
syn match astatus /\v\[\w+\]/
syn match areminder_fresh /\v\[remind me .*\]/
syn match areminder_awaiting /\v\[\^\d+:remind me .*\]/
syn match areminder_triggered /\v\[\!\d+:remind me .*\]/

syn region todoLine start=/^*/ end=/$/ oneline contains=person,task,diff,atag,astatus,areminder_fresh,areminder_awaiting,areminder_triggered
syn region completed start=/^+/ end=/$/ oneline contains=person,task,diff,atag,astatus,areminder_fresh,areminder_awaiting,areminder_triggered
syn region cancelled start=/^-/ end=/$/ oneline contains=person,task,diff,atag,astatus,areminder_fresh,areminder_awaiting,areminder_triggered
syn region separator start=/----------/ end=/$/ oneline


hi def link person Special
hi def link task Statement
hi def link diff DiffChange
hi def link atag Comment
hi def link areminder_awaiting Comment
hi def link areminder_fresh Label
hi def link areminder_triggered Error

hi def link todoline MoreMsg
hi def link completed Question
hi def link separator ColorColumn
hi def link cancelled Conseal
hi def link astatus Question
