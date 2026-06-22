import { IsEnum, IsUrl } from 'class-validator';
import { ComponentDomain } from '../enums';

export class PackageComponentDto {
  @IsUrl()
  repoUrl: string;

  @IsEnum(ComponentDomain)
  domain: ComponentDomain;
}
