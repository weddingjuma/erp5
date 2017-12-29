context.Base_createUITestLanguages()
param_dict = [
  { 'message': 'History', 'translation': 'lishi', 'language': 'wo'},
  { 'message': 'Cut', 'translation': 'jianque', 'language': 'wo'},
  { 'message': 'Proceed', 'translation': 'jixu', 'language': 'wo'},
  { 'message': 'Title', 'translation': 'biaoti', 'language': 'wo'},
  { 'message': 'Equals To', 'translation': 'dengyu', 'language': 'wo'},
  { 'message': 'Contains', 'translation': 'baohang', 'language': 'wo'},
  { 'message': 'Search', 'translation': 'soushuo', 'language': 'wo'},
  { 'message': 'Next', 'translation': 'houyige', 'language': 'wo'},
  { 'message': 'Add', 'translation': 'zhenjia', 'language': 'wo'},
  { 'message': 'Loading', 'translation': 'jiazhaizhong', 'language': 'wo'},
  { 'message': 'Actions', 'translation': 'caozhuo', 'language': 'wo'},
  { 'message': 'Explore the Search Result List', 'translation': 'liulangjieguo', 'language': 'wo'},
  { 'message': 'Save', 'translation': 'baochun', 'language': 'wo'},
  { 'message': 'Type', 'translation': 'leixing', 'language': 'wo'},
  { 'message': 'No records', 'translation': 'meiyoujilu', 'language': 'wo'},
  { 'message': 'Sort', 'translation': 'paixu', 'language': 'wo'},
  { 'message': 'Create New', 'translation': 'tianjia', 'language': 'wo'},
  { 'message': 'Description', 'translation': 'miaoshu', 'language': 'wo'},
  { 'message': 'Greater Than', 'translation': 'dayu', 'language': 'wo'},
  { 'message': 'Confirm', 'translation': 'queren', 'language': 'wo'},
  { 'message': 'Editable', 'translation': 'bianxue', 'language': 'wo'},
  { 'message': 'Less Than', 'translation': 'xiaoyu', 'language': 'wo'},
  { 'message': 'Records', 'translation': 'jilu', 'language': 'wo'},
  { 'message': 'All criterions (AND)', 'translation': 'fuheshuoyou', 'language': 'wo'},
  { 'message': 'Logout', 'translation': 'tuichu', 'language': 'wo'},
  { 'message': 'User', 'translation': 'yonghu', 'language': 'wo'},
  { 'message': 'Sort Editor', 'translation': 'paixubianyiqi', 'language': 'wo'},
  { 'message': 'Home', 'translation': 'zhuye', 'language': 'wo'},
  { 'message': 'State', 'translation': 'zhuangtai', 'language': 'wo'},
  { 'message': 'Preferences', 'translation': 'pianai', 'language': 'wo'},
  { 'message': 'Worklists', 'translation': 'gongzhuoliebiao', 'language': 'wo'},
  { 'message': 'Viewable', 'translation': 'shitujiemian', 'language': 'wo'},
  { 'message': 'Language', 'translation': 'yuyan', 'language': 'wo'},
  { 'message': 'Modules', 'translation': 'mokuai', 'language': 'wo'},
  { 'message': 'ascending', 'translation': 'shangshen', 'language': 'wo'},
  { 'message': 'Filter', 'translation': 'guolv', 'language': 'wo'},
  { 'message': 'Searchable Text', 'translation': 'soushuowenben', 'language': 'wo'},
  { 'message': 'Search Expression', 'translation': 'soushuo', 'language': 'wo'},
  { 'message': 'Close', 'translation': 'guangbi', 'language': 'wo'},
  { 'message': 'Worklist', 'translation': 'gongzhuoliebiao', 'language': 'wo'},
  { 'message': 'Delete', 'translation': 'shangchu', 'language': 'wo'},
  { 'message': 'Reference', 'translation': 'chankao', 'language': 'wo'},
  { 'message': 'Filter Editor', 'translation': 'guolvbianjiqi', 'language': 'wo'},
  { 'message': 'Select Template', 'translation': 'xuanzhemoban', 'language': 'wo'},
  { 'message': 'descending', 'translation': 'xiajiang', 'language': 'wo'},
  { 'message': 'Views', 'translation': 'shitu', 'language': 'wo'},
  { 'message': 'Hide Rows', 'translation': 'yanchanlie', 'language': 'wo'},
  { 'message': 'Jump', 'translation': 'tiaozhuan', 'language': 'wo'},
  { 'message': 'Export', 'translation': 'daochu', 'language': 'wo'},
  { 'message': 'At least one (OR)', 'translation': 'zhishaoyige', 'language': 'wo'},
  { 'message': 'Not Less Than', 'translation': 'dayudengyu', 'language': 'wo'},
  { 'message': 'Not Greater Than', 'translation': 'xiaoyudengyu', 'language': 'wo'},
  { 'message': 'Previous', 'translation': 'qianyige', 'language': 'wo'},
  { 'message': 'Web Pages', 'translation': 'wangye', 'language': 'wo'},
  { 'message': 'Draft To Validate', 'translation': 'daiyanzhen', 'language': 'wo'},
  { 'message': 'Foo', 'translation': 'Foo_zhongwen', 'language': 'wo'},
  { 'message': 'Published Alive', 'translation': 'gongbukexiugai', 'language': 'wo'},
  { 'message': 'Chinese', 'translation': 'zhongwen', 'language': 'wo'},
  { 'message': 'Foo Module', 'translation': 'foo_mokuai', 'language': 'wo'},
  { 'message': 'Foos', 'translation': 'foo_mokuai', 'language': 'wo'},
  { 'message': 'Validate Action', 'translation': 'yanzhen', 'language': 'wo'},
  { 'message': 'Validate', 'translation': 'yanzhen', 'language': 'wo'},
  { 'message': 'Login', 'translation': 'denglu', 'language': 'wo'},
  { 'message': 'Password', 'translation': 'mima', 'language': 'wo'},
  { 'message': 'I forgot my password!', 'translation': 'wanjimima', 'language': 'wo'},
  { 'message': 'Default', 'translation': 'moren', 'language': 'wo'},
  { 'message': 'Creation Date', 'translation': 'chuangjianshijian', 'language': 'wo'},
  { 'message': 'Modification Date', 'translation': 'xiugaishijian', 'language': 'wo'},
  { 'message': 'Owner', 'translation': 'shuoyouzhe', 'language': 'wo'},
  { 'message': 'Configure', 'translation': 'peizhi', 'language': 'wo'},
  { 'message': 'Configure Editor', 'translation': 'peizhibianjiqi', 'language': 'wo'},
  { 'message': 'This page contains unsaved changes, do you really want to leave the page ?', 'translation': 'querenlikai?', 'language': 'wo'}
]
for tmp in param_dict:
  context.Base_addUITestTranslation(message = tmp['message'], translation = tmp['translation'], language = tmp['language'])

context.web_site_module.renderjs_runner.setAvailableLanguageSet(['en', 'wo'])
context.web_site_module.renderjs_runner.Base_createTranslateData(translation_data_file='gadget_translation_data.js',batch_mode=1)
context.ERP5Site_updateTranslationTable()
return 'done'
