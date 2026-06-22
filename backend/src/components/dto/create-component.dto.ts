import { IsEnum, IsOptional, IsString } from 'class-validator';
import { ComponentDomain } from '../enums';

export class CreateComponentDto {
  @IsString()
  name: string;

  @IsString()
  @IsOptional()
  dockerfileContent?: string;

  @IsEnum(ComponentDomain)
  domain: ComponentDomain;
}
