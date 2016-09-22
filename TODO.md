* Implement argparse:
  * take review id to create spec for new module under review
  * allow to specify where to check out upstream modules (besides tmp)
  * allow to specifiy if using checked-out rdoinfo repo
* Make structure class-based and more modular.
* Extract common tasks to a base class, so there is option to have specific
  child classes for different types of projects in future besides puppet.
* Add tests
* Add structure to allow beter packaging of this module.
* Abstract out special cases of files that a given project needs (puppet-nova is
  current example)
* Make Source be a list and then iterate over it and name them accordingly
  (Source0, Source1, etc.), like the metadata.dependencies.
